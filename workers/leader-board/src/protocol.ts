// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Wire protocol types and validation for the leader board WebSocket protocol.
 *
 * Frame types match SPEC.md Wire Protocol section exactly. Clients cannot
 * distinguish between the DO adapter and the local server adapter.
 */

// --- Constants ---

const CHANNEL_NAME_RE = /^[a-zA-Z0-9_-]{1,128}$/;
const MESSAGE_MAX_BYTES = 1_048_576; // 1 MB

// --- Handshake Frames ---

export interface ChallengeFrame {
  type: "challenge";
  nonce: string;
}

export interface AuthFrame {
  type: "auth";
  swarm: string;
  signature: string;
}

export interface RegisterSwarmFrame {
  type: "register_swarm";
  swarm: string;
  public_key: string;
}

export interface AuthOkFrame {
  type: "auth_ok";
}

// --- Client → Server Frames (Post-Auth) ---

export interface WatchFrame {
  type: "watch";
  channel: string;
  swarm: string;
  cursor: number;
}

export interface SendFrame {
  type: "send";
  channel: string;
  swarm: string;
  body: string;
}

export interface ChannelsFrame {
  type: "channels";
  swarm: string;
}

export interface SwarmInfoFrame {
  type: "swarm_info";
  swarm: string;
}

// --- Server → Client Frames ---

export interface MessageFrame {
  type: "message";
  channel: string;
  position: number;
  body: string;
  sent_at: string;
}

export interface AckFrame {
  type: "ack";
  channel: string;
  position: number;
}

export interface ChannelsListFrame {
  type: "channels_list";
  channels: Array<{ name: string; head_position: number; oldest_position: number }>;
}

export interface SwarmInfoResponseFrame {
  type: "swarm_info";
  swarm: string;
  created_at: string;
}

export interface ErrorFrame {
  type: "error";
  code: string;
  message: string;
  earliest_position?: number;
}

// --- Discriminated Unions ---

export type HandshakeClientFrame = AuthFrame | RegisterSwarmFrame;
export type PostAuthClientFrame = WatchFrame | SendFrame | ChannelsFrame | SwarmInfoFrame;
export type ClientFrame = HandshakeClientFrame | PostAuthClientFrame;
export type ServerFrame =
  | ChallengeFrame
  | AuthOkFrame
  | MessageFrame
  | AckFrame
  | ChannelsListFrame
  | SwarmInfoResponseFrame
  | ErrorFrame;

// --- Parsing ---

export class ProtocolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ProtocolError";
  }
}

function requireString(obj: Record<string, unknown>, field: string): string {
  const val = obj[field];
  if (typeof val !== "string" || val.length === 0) {
    throw new ProtocolError(`Missing or invalid field: ${field}`);
  }
  return val;
}

function requireNonNegativeInt(obj: Record<string, unknown>, field: string): number {
  const val = obj[field];
  if (typeof val !== "number" || !Number.isInteger(val) || val < 0) {
    throw new ProtocolError(`Missing or invalid field: ${field} (must be a non-negative integer)`);
  }
  return val;
}

function validateChannelName(name: string): void {
  if (!CHANNEL_NAME_RE.test(name)) {
    throw new ProtocolError(
      `Invalid channel name: "${name}" (must match ${CHANNEL_NAME_RE.source})`
    );
  }
}

/**
 * Parse a raw JSON string into a typed handshake client frame.
 * Throws ProtocolError on invalid input.
 */
export function parseHandshakeFrame(raw: string): HandshakeClientFrame {
  let obj: Record<string, unknown>;
  try {
    obj = JSON.parse(raw);
  } catch {
    throw new ProtocolError("Invalid JSON");
  }

  if (typeof obj !== "object" || obj === null || Array.isArray(obj)) {
    throw new ProtocolError("Frame must be a JSON object");
  }

  const type = obj.type;

  switch (type) {
    case "auth":
      return {
        type: "auth",
        swarm: requireString(obj, "swarm"),
        signature: requireString(obj, "signature"),
      };
    case "register_swarm":
      return {
        type: "register_swarm",
        swarm: requireString(obj, "swarm"),
        public_key: requireString(obj, "public_key"),
      };
    default:
      throw new ProtocolError(`Unexpected handshake frame type: ${String(type)}`);
  }
}

/**
 * Parse a raw JSON string into a typed post-auth client frame.
 * Throws ProtocolError on invalid input.
 */
export function parsePostAuthFrame(raw: string): PostAuthClientFrame {
  let obj: Record<string, unknown>;
  try {
    obj = JSON.parse(raw);
  } catch {
    throw new ProtocolError("Invalid JSON");
  }

  if (typeof obj !== "object" || obj === null || Array.isArray(obj)) {
    throw new ProtocolError("Frame must be a JSON object");
  }

  const type = obj.type;

  switch (type) {
    case "watch": {
      const channel = requireString(obj, "channel");
      validateChannelName(channel);
      return {
        type: "watch",
        channel,
        swarm: requireString(obj, "swarm"),
        cursor: requireNonNegativeInt(obj, "cursor"),
      };
    }
    case "send": {
      const channel = requireString(obj, "channel");
      validateChannelName(channel);
      const body = requireString(obj, "body");
      // Validate body size (base64 encoded — decode to check actual size)
      const decodedSize = Math.ceil((body.length * 3) / 4);
      if (decodedSize > MESSAGE_MAX_BYTES) {
        throw new ProtocolError(
          `Message body too large: ~${decodedSize} bytes (max ${MESSAGE_MAX_BYTES})`
        );
      }
      return {
        type: "send",
        channel,
        swarm: requireString(obj, "swarm"),
        body,
      };
    }
    case "channels":
      return {
        type: "channels",
        swarm: requireString(obj, "swarm"),
      };
    case "swarm_info":
      return {
        type: "swarm_info",
        swarm: requireString(obj, "swarm"),
      };
    default:
      throw new ProtocolError(`Unknown frame type: ${String(type)}`);
  }
}

/** Serialize a server frame to JSON string. */
export function serializeFrame(frame: ServerFrame): string {
  return JSON.stringify(frame);
}
