// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * SwarmDO — Durable Object class for a single swarm.
 *
 * One DO instance per swarm. Owns all state: channels, messages,
 * public key. Implements the wire protocol handshake and post-auth
 * frame handlers. Uses DO alarms for compaction scheduling.
 */

import { generateChallenge, verifySignature } from "./auth";
import {
  type PostAuthClientFrame,
  type ServerFrame,
  ProtocolError,
  parseHandshakeFrame,
  parsePostAuthFrame,
  serializeFrame,
} from "./protocol";
import { SwarmStorage } from "./storage";

const COMPACTION_INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 hours
const COMPACTION_MIN_AGE_DAYS = 30;

interface Watcher {
  ws: WebSocket;
  cursor: number;
}

// Chunk: docs/chunks/leader_board_hibernate_watch - WebSocket attachment schema
interface WsAttachment {
  state: "handshake" | "authenticated";
  nonce?: string;
  watching?: { channel: string; cursor: number };
}

export class SwarmDO implements DurableObject {
  private storage: SwarmStorage;
  private ctx: DurableObjectState;

  // Per-channel watcher sets for blocking read wake-up
  private watchers: Map<string, Set<Watcher>> = new Map();

  constructor(ctx: DurableObjectState, _env: Env) {
    this.ctx = ctx;
    this.storage = new SwarmStorage(ctx.storage);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Chunk: docs/chunks/gateway_token_storage - HTTP routes for gateway key storage
    if (url.pathname.startsWith("/gateway/keys")) {
      return this.handleGatewayKeys(request, url);
    }

    // Only accept WebSocket upgrades
    const upgradeHeader = request.headers.get("Upgrade");
    if (!upgradeHeader || upgradeHeader.toLowerCase() !== "websocket") {
      return new Response("Expected WebSocket upgrade", { status: 426 });
    }

    const pair = new WebSocketPair();
    const [client, server] = [pair[0], pair[1]];

    // Use the Hibernation API for cost efficiency
    this.ctx.acceptWebSocket(server);

    // Send challenge immediately
    const nonce = generateChallenge();
    // Store nonce on the WebSocket for later verification
    server.serializeAttachment({ state: "handshake", nonce });

    const challengeFrame: ServerFrame = { type: "challenge", nonce };
    server.send(serializeFrame(challengeFrame));

    return new Response(null, { status: 101, webSocket: client });
  }

  // Chunk: docs/chunks/gateway_token_storage - Gateway key CRUD handler
  private async handleGatewayKeys(
    request: Request,
    url: URL
  ): Promise<Response> {
    const jsonHeaders = { "Content-Type": "application/json" };

    // Extract token_hash from path: /gateway/keys/{token_hash}
    const pathParts = url.pathname.split("/");
    // pathParts: ["", "gateway", "keys", token_hash?]
    const tokenHashFromPath = pathParts.length > 3 ? pathParts[3] : null;

    switch (request.method) {
      case "PUT": {
        let body: { token_hash?: string; encrypted_blob?: string };
        try {
          body = (await request.json()) as {
            token_hash?: string;
            encrypted_blob?: string;
          };
        } catch {
          return new Response(
            JSON.stringify({ error: "Invalid JSON body" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        if (
          !body.token_hash ||
          typeof body.token_hash !== "string" ||
          !body.encrypted_blob ||
          typeof body.encrypted_blob !== "string"
        ) {
          return new Response(
            JSON.stringify({
              error: "Missing required fields: token_hash, encrypted_blob",
            }),
            { status: 400, headers: jsonHeaders }
          );
        }

        this.storage.putGatewayKey(body.token_hash, body.encrypted_blob);
        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: jsonHeaders,
        });
      }

      case "GET": {
        if (!tokenHashFromPath) {
          return new Response(
            JSON.stringify({ error: "Missing token_hash in path" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        const key = this.storage.getGatewayKey(tokenHashFromPath);
        if (!key) {
          return new Response(
            JSON.stringify({ error: "Key not found" }),
            { status: 404, headers: jsonHeaders }
          );
        }

        return new Response(JSON.stringify(key), {
          status: 200,
          headers: jsonHeaders,
        });
      }

      case "DELETE": {
        if (!tokenHashFromPath) {
          return new Response(
            JSON.stringify({ error: "Missing token_hash in path" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        const deleted = this.storage.deleteGatewayKey(tokenHashFromPath);
        if (!deleted) {
          return new Response(
            JSON.stringify({ error: "Key not found" }),
            { status: 404, headers: jsonHeaders }
          );
        }

        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: jsonHeaders,
        });
      }

      default:
        return new Response(
          JSON.stringify({ error: "Method not allowed" }),
          { status: 405, headers: jsonHeaders }
        );
    }
  }

  // --- Hibernation API handlers ---

  async webSocketMessage(ws: WebSocket, message: string | ArrayBuffer): Promise<void> {
    const raw = typeof message === "string" ? message : new TextDecoder().decode(message);
    const attachment = ws.deserializeAttachment() as WsAttachment;

    if (attachment.state === "handshake") {
      await this.handleHandshake(ws, raw, attachment.nonce!);
    } else {
      await this.handlePostAuth(ws, raw);
    }
  }

  async webSocketClose(ws: WebSocket, _code: number, _reason: string, _wasClean: boolean): Promise<void> {
    this.removeWatcher(ws);
  }

  async webSocketError(ws: WebSocket, _error: unknown): Promise<void> {
    this.removeWatcher(ws);
  }

  async alarm(): Promise<void> {
    // Compaction sweep
    const channels = this.storage.listChannels();
    for (const ch of channels) {
      this.storage.compact(ch.name, COMPACTION_MIN_AGE_DAYS);
    }
    // Re-schedule
    await this.ctx.storage.setAlarm(Date.now() + COMPACTION_INTERVAL_MS);
  }

  // --- Handshake ---

  private async handleHandshake(ws: WebSocket, raw: string, nonce: string): Promise<void> {
    try {
      const frame = parseHandshakeFrame(raw);

      if (frame.type === "register_swarm") {
        this.storage.saveSwarm(frame.swarm, frame.public_key);
        ws.serializeAttachment({ state: "authenticated" });
        ws.send(serializeFrame({ type: "auth_ok" }));
        // Schedule compaction alarm if not already set
        await this.ensureAlarm();
      } else if (frame.type === "auth") {
        const swarm = this.storage.getSwarm();
        if (!swarm) {
          this.sendError(ws, "swarm_not_found", "Swarm not registered");
          ws.close(1008, "Swarm not registered");
          return;
        }

        const valid = await verifySignature(swarm.public_key, nonce, frame.signature);
        if (!valid) {
          this.sendError(ws, "auth_failed", "Signature verification failed");
          ws.close(1008, "Auth failed");
          return;
        }

        ws.serializeAttachment({ state: "authenticated" });
        ws.send(serializeFrame({ type: "auth_ok" }));
      }
    } catch (e) {
      if (e instanceof ProtocolError) {
        this.sendError(ws, "invalid_frame", e.message);
      } else {
        this.sendError(ws, "invalid_frame", "Failed to parse handshake frame");
      }
      ws.close(1008, "Invalid handshake");
    }
  }

  // --- Post-Auth Frame Handling ---

  private async handlePostAuth(ws: WebSocket, raw: string): Promise<void> {
    let frame: PostAuthClientFrame;
    try {
      frame = parsePostAuthFrame(raw);
    } catch (e) {
      if (e instanceof ProtocolError) {
        this.sendError(ws, "invalid_frame", e.message);
      } else {
        this.sendError(ws, "invalid_frame", "Failed to parse frame");
      }
      return;
    }

    switch (frame.type) {
      case "send":
        this.handleSend(ws, frame);
        break;
      case "watch":
        this.handleWatch(ws, frame);
        break;
      case "channels":
        this.handleChannels(ws);
        break;
      case "swarm_info":
        this.handleSwarmInfo(ws);
        break;
    }
  }

  private handleSend(
    ws: WebSocket,
    frame: { channel: string; body: string }
  ): void {
    const result = this.storage.appendMessage(frame.channel, frame.body);

    // Send ack
    const ackFrame: ServerFrame = {
      type: "ack",
      channel: frame.channel,
      position: result.position,
    };
    ws.send(serializeFrame(ackFrame));

    // Wake watchers on this channel
    this.wakeWatchers(frame.channel, result.position);

    // Ensure compaction alarm is scheduled
    this.ensureAlarm();
  }

  private handleWatch(
    ws: WebSocket,
    frame: { channel: string; cursor: number }
  ): void {
    // Check if channel exists
    const chInfo = this.storage.getChannelInfo(frame.channel);

    if (!chInfo) {
      this.sendError(ws, "channel_not_found", `Channel not found: ${frame.channel}`);
      return;
    }

    // Check cursor validity
    if (frame.cursor + 1 < chInfo.oldest_position) {
      const errFrame: ServerFrame = {
        type: "error",
        code: "cursor_expired",
        message: `Cursor expired; earliest available position: ${chInfo.oldest_position}`,
        earliest_position: chInfo.oldest_position,
      };
      ws.send(serializeFrame(errFrame));
      return;
    }

    // Try to read immediately
    const msg = this.storage.readAfter(frame.channel, frame.cursor);
    if (msg) {
      const msgFrame: ServerFrame = {
        type: "message",
        channel: msg.channel,
        position: msg.position,
        body: msg.body,
        sent_at: msg.sent_at,
      };
      ws.send(serializeFrame(msgFrame));
      return;
    }

    // No message yet — register as pending watcher
    let channelWatchers = this.watchers.get(frame.channel);
    if (!channelWatchers) {
      channelWatchers = new Set();
      this.watchers.set(frame.channel, channelWatchers);
    }
    channelWatchers.add({ ws, cursor: frame.cursor });

    // Chunk: docs/chunks/leader_board_hibernate_watch - Persist watch state for hibernation recovery
    const attachment = ws.deserializeAttachment() as WsAttachment;
    attachment.watching = { channel: frame.channel, cursor: frame.cursor };
    ws.serializeAttachment(attachment);
  }

  private handleChannels(ws: WebSocket): void {
    const channels = this.storage.listChannels();
    const frame: ServerFrame = {
      type: "channels_list",
      channels: channels.map((ch) => ({
        name: ch.name,
        head_position: ch.head_position,
        oldest_position: ch.oldest_position,
      })),
    };
    ws.send(serializeFrame(frame));
  }

  private handleSwarmInfo(ws: WebSocket): void {
    const swarm = this.storage.getSwarm();
    if (!swarm) {
      this.sendError(ws, "swarm_not_found", "Swarm not registered");
      return;
    }
    const frame: ServerFrame = {
      type: "swarm_info",
      swarm: swarm.swarm_id,
      created_at: swarm.created_at,
    };
    ws.send(serializeFrame(frame));
  }

  // --- Watcher Management ---

  private wakeWatchers(channel: string, newPosition: number): void {
    // 1. Try in-memory watchers first (fast path, no hibernation)
    const channelWatchers = this.watchers.get(channel);
    if (channelWatchers && channelWatchers.size > 0) {
      const toRemove: Watcher[] = [];

      for (const watcher of channelWatchers) {
        if (watcher.cursor < newPosition) {
          // Read the message for this watcher
          const msg = this.storage.readAfter(channel, watcher.cursor);
          if (msg) {
            try {
              const msgFrame: ServerFrame = {
                type: "message",
                channel: msg.channel,
                position: msg.position,
                body: msg.body,
                sent_at: msg.sent_at,
              };
              watcher.ws.send(serializeFrame(msgFrame));
              // Clear watch state from attachment after delivery
              const att = watcher.ws.deserializeAttachment() as WsAttachment;
              delete att.watching;
              watcher.ws.serializeAttachment(att);
            } catch {
              // WebSocket may have closed — will be cleaned up
            }
            toRemove.push(watcher);
          }
        }
      }

      for (const w of toRemove) {
        channelWatchers.delete(w);
      }
      if (channelWatchers.size === 0) {
        this.watchers.delete(channel);
      }
      return;
    }

    // 2. Hibernation recovery: scan all connected WebSockets
    // Chunk: docs/chunks/leader_board_hibernate_watch - Recover watchers after hibernation
    const allSockets = this.ctx.getWebSockets();
    for (const ws of allSockets) {
      try {
        const attachment = ws.deserializeAttachment() as WsAttachment;
        if (
          attachment?.watching?.channel === channel &&
          attachment.watching.cursor < newPosition
        ) {
          const msg = this.storage.readAfter(channel, attachment.watching.cursor);
          if (msg) {
            const msgFrame: ServerFrame = {
              type: "message",
              channel: msg.channel,
              position: msg.position,
              body: msg.body,
              sent_at: msg.sent_at,
            };
            ws.send(serializeFrame(msgFrame));
            // Clear watch state after delivery
            delete attachment.watching;
            ws.serializeAttachment(attachment);
          }
        }
      } catch {
        // WebSocket may have closed
      }
    }
  }

  private removeWatcher(ws: WebSocket): void {
    // Clear in-memory state
    for (const [channel, watchers] of this.watchers) {
      for (const watcher of watchers) {
        if (watcher.ws === ws) {
          watchers.delete(watcher);
        }
      }
      if (watchers.size === 0) {
        this.watchers.delete(channel);
      }
    }

    // Chunk: docs/chunks/leader_board_hibernate_watch - Clear attachment watch state
    try {
      const attachment = ws.deserializeAttachment() as WsAttachment;
      if (attachment?.watching) {
        delete attachment.watching;
        ws.serializeAttachment(attachment);
      }
    } catch {
      // WebSocket may already be closed/invalid
    }
  }

  // --- Test Helpers ---

  /** @internal Clear in-memory watcher state to simulate hibernation memory loss. Test-only. */
  _clearWatchersForTest(): void {
    this.watchers.clear();
  }

  // --- Helpers ---

  private sendError(ws: WebSocket, code: string, message: string): void {
    try {
      ws.send(serializeFrame({ type: "error", code, message }));
    } catch {
      // WebSocket may already be closed
    }
  }

  private async ensureAlarm(): Promise<void> {
    const existing = await this.ctx.storage.getAlarm();
    if (!existing) {
      await this.ctx.storage.setAlarm(Date.now() + COMPACTION_INTERVAL_MS);
    }
  }
}

export interface Env {
  SWARM_DO: DurableObjectNamespace;
}
