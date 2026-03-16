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
  hashToken,
  decryptBlob,
  deriveSymmetricKey,
  decryptMessage,
  encryptMessage,
} from "./gateway-crypto";
import {
  type PostAuthClientFrame,
  type ServerFrame,
  ProtocolError,
  parseHandshakeFrame,
  parsePostAuthFrame,
  serializeFrame,
} from "./protocol";
import { SwarmStorage, type StoredMessage, type ChannelInfo } from "./storage";

// Chunk: docs/chunks/invite_instruction_page - Render invite instruction page
function renderInvitePage(
  origin: string,
  token: string,
  swarmId: string,
  channels: ChannelInfo[]
): string {
  const exampleChannel = channels.length > 0 ? channels[0].name : "changelog";

  let channelSection: string;
  if (channels.length === 0) {
    channelSection = "No channels exist yet. Post a message to create one.";
  } else {
    channelSection = channels
      .map((ch) => `- ${ch.name} (${ch.head_position} messages)`)
      .join("\n");
  }

  return `# Swarm Invite — ${swarmId}

You have been invited to participate in a swarm via the HTTP gateway.
Your token grants read and write access to all channels.

## Available Channels

${channelSection}

## Reading Messages

  curl '${origin}/gateway/${token}/channels/${exampleChannel}/messages?after=0&swarm=${swarmId}'

Query parameters:
- after={position} — return messages after this position (default: 0)
- limit={n} — max messages to return (default: 50, max: 200)
- wait={seconds} — long-poll: block up to N seconds for new messages (1-60)

## Posting Messages

  curl -X POST '${origin}/gateway/${token}/channels/${exampleChannel}/messages?swarm=${swarmId}' \\
    -H 'Content-Type: application/json' \\
    -d '{"body": "your message here"}'

## Polling Loop

To continuously watch a channel:

  CURSOR=0
  while true; do
    RESP=$(curl -s '${origin}/gateway/${token}/channels/${exampleChannel}/messages?after=$CURSOR&wait=30&swarm=${swarmId}')
    # Process messages, update CURSOR to latest position
    sleep 1
  done

## Security

- Your token is the sole credential. Keep it secret.
- The token grants access to ALL channels in this swarm.
- To revoke access, the swarm operator deletes the token server-side.
- Messages are encrypted in transit (TLS) and at rest on the server.
`;
}

const COMPACTION_INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 hours
const COMPACTION_MIN_AGE_DAYS = 30;
const CHANNEL_NAME_RE = /^[a-zA-Z0-9_-]{1,128}$/;
const GATEWAY_MESSAGE_MAX_BYTES = 1_048_576; // 1 MB

// Chunk: docs/chunks/gateway_cleartext_api - Long-poll pending poll type
interface PendingPoll {
  channel: string;
  cursor: number;
  limit: number;
  symmetricKey: Uint8Array;
  resolve: (response: Response) => void;
  timer: ReturnType<typeof setTimeout>;
}

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
  // Chunk: docs/chunks/invite_path_routing_fix - Store env for KV access
  private env: Env;

  // Per-channel watcher sets for blocking read wake-up
  private watchers: Map<string, Set<Watcher>> = new Map();

  // Chunk: docs/chunks/gateway_cleartext_api - Long-poll pending polls
  private pendingPolls: Map<string, Set<PendingPoll>> = new Map();

  constructor(ctx: DurableObjectState, env: Env) {
    this.ctx = ctx;
    this.env = env;
    this.storage = new SwarmStorage(ctx.storage);
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    // Chunk: docs/chunks/gateway_token_storage - HTTP routes for gateway key storage
    if (url.pathname.startsWith("/gateway/keys")) {
      return this.handleGatewayKeys(request, url);
    }

    // Chunk: docs/chunks/invite_instruction_page - Invite instruction page route
    const inviteMatch = url.pathname.match(/^\/invite\/([^/]+)$/);
    if (inviteMatch) {
      return this.handleInvitePage(request, url, inviteMatch[1]);
    }

    // Chunk: docs/chunks/gateway_cleartext_api - Cleartext gateway HTTP handler
    const gatewayMatch = url.pathname.match(
      /^\/gateway\/([^/]+)\/channels\/([^/]+)\/messages$/
    );
    if (gatewayMatch) {
      return this.handleGatewayAPI(request, url, gatewayMatch[1], gatewayMatch[2]);
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

        // Chunk: docs/chunks/invite_instruction_page - Pass swarm_id for invite routing
        const swarmId = url.searchParams.get("swarm") || "";
        this.storage.putGatewayKey(body.token_hash, body.encrypted_blob, swarmId);
        // Chunk: docs/chunks/invite_path_routing_fix - Write token→swarm KV index
        await this.env.TOKEN_SWARM_INDEX.put(body.token_hash, swarmId);
        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: jsonHeaders,
        });
      }

      case "GET": {
        // Chunk: docs/chunks/invite_list_revoke - List all keys when no token_hash in path
        if (!tokenHashFromPath) {
          const keys = this.storage.listGatewayKeys();
          const keysWithHint = keys.map((k) => ({
            token_hash: k.token_hash,
            created_at: k.created_at,
            hint: k.token_hash.substring(0, 8),
          }));
          return new Response(JSON.stringify({ keys: keysWithHint }), {
            status: 200,
            headers: jsonHeaders,
          });
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
        // Chunk: docs/chunks/invite_list_revoke - Bulk delete when no token_hash in path
        if (!tokenHashFromPath) {
          // Chunk: docs/chunks/invite_path_routing_fix - Clean up KV index before bulk delete
          const allKeys = this.storage.listGatewayKeys();
          const deletedCount = this.storage.deleteAllGatewayKeys();
          for (const key of allKeys) {
            await this.env.TOKEN_SWARM_INDEX.delete(key.token_hash);
          }
          return new Response(
            JSON.stringify({ ok: true, deleted: deletedCount }),
            { status: 200, headers: jsonHeaders }
          );
        }

        const deleted = this.storage.deleteGatewayKey(tokenHashFromPath);
        if (!deleted) {
          return new Response(
            JSON.stringify({ error: "Key not found" }),
            { status: 404, headers: jsonHeaders }
          );
        }

        // Chunk: docs/chunks/invite_path_routing_fix - Remove token→swarm KV entry
        await this.env.TOKEN_SWARM_INDEX.delete(tokenHashFromPath);
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

  // Chunk: docs/chunks/invite_instruction_page - Invite instruction page handler
  private async handleInvitePage(
    request: Request,
    url: URL,
    token: string
  ): Promise<Response> {
    if (request.method !== "GET") {
      return new Response("Method not allowed", { status: 405 });
    }

    // Validate token
    const tokenHash = hashToken(token);
    const keyRecord = this.storage.getGatewayKey(tokenHash);
    if (!keyRecord) {
      return new Response("Invalid or expired invite token", {
        status: 404,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    // Fetch swarm metadata and channels
    const swarm = this.storage.getSwarm();
    const swarmId = url.searchParams.get("swarm") || swarm?.swarm_id || "unknown";
    const channels = this.storage.listChannels();
    const origin = url.origin;

    const content = renderInvitePage(origin, token, swarmId, channels);
    return new Response(content, {
      status: 200,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  // Chunk: docs/chunks/gateway_cleartext_api - Cleartext gateway HTTP handler
  private async handleGatewayAPI(
    request: Request,
    url: URL,
    token: string,
    channel: string
  ): Promise<Response> {
    const jsonHeaders = { "Content-Type": "application/json" };

    // Validate channel name
    if (!CHANNEL_NAME_RE.test(channel)) {
      return new Response(
        JSON.stringify({ error: `Invalid channel name: "${channel}"` }),
        { status: 400, headers: jsonHeaders }
      );
    }

    // Resolve token → encrypted blob → seed → symmetric key
    let symmetricKey: Uint8Array;
    try {
      const tokenHash = hashToken(token);
      const keyRecord = this.storage.getGatewayKey(tokenHash);
      if (!keyRecord) {
        return new Response(
          JSON.stringify({ error: "Invalid or revoked token" }),
          { status: 401, headers: jsonHeaders }
        );
      }

      const seed = decryptBlob(keyRecord.encrypted_blob, token);
      symmetricKey = deriveSymmetricKey(seed);
    } catch {
      return new Response(
        JSON.stringify({ error: "Invalid or revoked token" }),
        { status: 401, headers: jsonHeaders }
      );
    }

    switch (request.method) {
      case "GET": {
        const afterParam = url.searchParams.get("after");
        const cursor = afterParam !== null ? parseInt(afterParam, 10) : 0;
        if (isNaN(cursor) || cursor < 0) {
          return new Response(
            JSON.stringify({ error: "Invalid 'after' parameter" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        const limitParam = url.searchParams.get("limit");
        let limit = 50;
        if (limitParam !== null) {
          limit = parseInt(limitParam, 10);
          if (isNaN(limit) || limit < 1) limit = 50;
          if (limit > 200) limit = 200;
        }

        // Read messages
        const messages = this.storage.readAfterBatch(channel, cursor, limit);

        // If messages exist, return immediately
        if (messages.length > 0) {
          const decrypted = messages.map((msg) => ({
            position: msg.position,
            body: decryptMessage(msg.body, symmetricKey),
            sent_at: msg.sent_at,
          }));
          return new Response(JSON.stringify({ messages: decrypted }), {
            status: 200,
            headers: jsonHeaders,
          });
        }

        // Long-poll support
        const waitParam = url.searchParams.get("wait");
        if (waitParam !== null) {
          let waitSeconds = parseInt(waitParam, 10);
          if (isNaN(waitSeconds) || waitSeconds < 1) waitSeconds = 1;
          if (waitSeconds > 60) waitSeconds = 60;

          return new Promise<Response>((resolve) => {
            const timer = setTimeout(() => {
              // Timeout — remove poll and return empty
              this.removePendingPoll(channel, poll);
              resolve(
                new Response(JSON.stringify({ messages: [] }), {
                  status: 200,
                  headers: jsonHeaders,
                })
              );
            }, waitSeconds * 1000);

            const poll: PendingPoll = {
              channel,
              cursor,
              limit,
              symmetricKey,
              resolve,
              timer,
            };

            let channelPolls = this.pendingPolls.get(channel);
            if (!channelPolls) {
              channelPolls = new Set();
              this.pendingPolls.set(channel, channelPolls);
            }
            channelPolls.add(poll);
          });
        }

        // No wait param, return empty immediately
        return new Response(JSON.stringify({ messages: [] }), {
          status: 200,
          headers: jsonHeaders,
        });
      }

      case "POST": {
        let body: { body?: string };
        try {
          body = (await request.json()) as { body?: string };
        } catch {
          return new Response(
            JSON.stringify({ error: "Invalid JSON body" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        if (!body.body || typeof body.body !== "string") {
          return new Response(
            JSON.stringify({ error: "Missing required field: body" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        // Check body size
        const bodyBytes = new TextEncoder().encode(body.body);
        if (bodyBytes.length > GATEWAY_MESSAGE_MAX_BYTES) {
          return new Response(
            JSON.stringify({ error: "Message body too large" }),
            { status: 400, headers: jsonHeaders }
          );
        }

        // Encrypt and store
        const ciphertext = encryptMessage(body.body, symmetricKey);
        const result = this.storage.appendMessage(channel, ciphertext);

        // Wake WebSocket watchers and pending polls
        this.wakeWatchers(channel, result.position);
        this.wakePendingPolls(channel);

        // Ensure compaction alarm is scheduled
        await this.ensureAlarm();

        return new Response(
          JSON.stringify({ position: result.position, channel }),
          { status: 200, headers: jsonHeaders }
        );
      }

      default:
        return new Response(
          JSON.stringify({ error: "Method not allowed" }),
          { status: 405, headers: jsonHeaders }
        );
    }
  }

  // Chunk: docs/chunks/gateway_cleartext_api - Wake pending long-polls
  private wakePendingPolls(channel: string): void {
    const channelPolls = this.pendingPolls.get(channel);
    if (!channelPolls || channelPolls.size === 0) return;

    const jsonHeaders = { "Content-Type": "application/json" };

    for (const poll of channelPolls) {
      clearTimeout(poll.timer);
      try {
        const messages = this.storage.readAfterBatch(
          poll.channel,
          poll.cursor,
          poll.limit
        );
        const decrypted = messages.map((msg) => ({
          position: msg.position,
          body: decryptMessage(msg.body, poll.symmetricKey),
          sent_at: msg.sent_at,
        }));
        poll.resolve(
          new Response(JSON.stringify({ messages: decrypted }), {
            status: 200,
            headers: jsonHeaders,
          })
        );
      } catch {
        poll.resolve(
          new Response(JSON.stringify({ messages: [] }), {
            status: 200,
            headers: jsonHeaders,
          })
        );
      }
    }

    this.pendingPolls.delete(channel);
  }

  private removePendingPoll(channel: string, poll: PendingPoll): void {
    const channelPolls = this.pendingPolls.get(channel);
    if (channelPolls) {
      channelPolls.delete(poll);
      if (channelPolls.size === 0) {
        this.pendingPolls.delete(channel);
      }
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
  // Chunk: docs/chunks/invite_path_routing_fix - KV index for token→swarm resolution
  TOKEN_SWARM_INDEX: KVNamespace;
}
