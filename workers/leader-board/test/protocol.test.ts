// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
import { describe, it, expect } from "vitest";
import {
  parseHandshakeFrame,
  parsePostAuthFrame,
  ProtocolError,
} from "../src/protocol";

describe("parseHandshakeFrame", () => {
  it("parses a valid auth frame", () => {
    const frame = parseHandshakeFrame(
      JSON.stringify({ type: "auth", swarm: "swarm-1", signature: "deadbeef" })
    );
    expect(frame).toEqual({ type: "auth", swarm: "swarm-1", signature: "deadbeef" });
  });

  it("parses a valid register_swarm frame", () => {
    const frame = parseHandshakeFrame(
      JSON.stringify({
        type: "register_swarm",
        swarm: "swarm-1",
        public_key: "aabbccdd",
      })
    );
    expect(frame).toEqual({
      type: "register_swarm",
      swarm: "swarm-1",
      public_key: "aabbccdd",
    });
  });

  it("throws on invalid JSON", () => {
    expect(() => parseHandshakeFrame("not json")).toThrow(ProtocolError);
  });

  it("throws on missing swarm field in auth", () => {
    expect(() =>
      parseHandshakeFrame(JSON.stringify({ type: "auth", signature: "sig" }))
    ).toThrow(ProtocolError);
  });

  it("throws on missing public_key in register_swarm", () => {
    expect(() =>
      parseHandshakeFrame(JSON.stringify({ type: "register_swarm", swarm: "s1" }))
    ).toThrow(ProtocolError);
  });

  it("throws on unexpected frame type", () => {
    expect(() =>
      parseHandshakeFrame(JSON.stringify({ type: "watch", channel: "ch" }))
    ).toThrow(ProtocolError);
  });

  it("throws on non-object input", () => {
    expect(() => parseHandshakeFrame(JSON.stringify([1, 2, 3]))).toThrow(
      ProtocolError
    );
  });
});

describe("parsePostAuthFrame", () => {
  it("parses a valid watch frame", () => {
    const frame = parsePostAuthFrame(
      JSON.stringify({ type: "watch", channel: "ch-1", swarm: "s1", cursor: 0 })
    );
    expect(frame).toEqual({ type: "watch", channel: "ch-1", swarm: "s1", cursor: 0 });
  });

  it("parses a valid send frame", () => {
    const frame = parsePostAuthFrame(
      JSON.stringify({ type: "send", channel: "ch-1", swarm: "s1", body: "aGVsbG8=" })
    );
    expect(frame).toEqual({
      type: "send",
      channel: "ch-1",
      swarm: "s1",
      body: "aGVsbG8=",
    });
  });

  it("parses a valid channels frame", () => {
    const frame = parsePostAuthFrame(
      JSON.stringify({ type: "channels", swarm: "s1" })
    );
    expect(frame).toEqual({ type: "channels", swarm: "s1" });
  });

  it("parses a valid swarm_info frame", () => {
    const frame = parsePostAuthFrame(
      JSON.stringify({ type: "swarm_info", swarm: "s1" })
    );
    expect(frame).toEqual({ type: "swarm_info", swarm: "s1" });
  });

  it("throws on invalid channel name with spaces", () => {
    expect(() =>
      parsePostAuthFrame(
        JSON.stringify({ type: "watch", channel: "bad channel", swarm: "s1", cursor: 0 })
      )
    ).toThrow(ProtocolError);
  });

  it("throws on invalid channel name with special chars", () => {
    expect(() =>
      parsePostAuthFrame(
        JSON.stringify({ type: "send", channel: "ch@!#", swarm: "s1", body: "x" })
      )
    ).toThrow(ProtocolError);
  });

  it("throws on channel name exceeding 128 chars", () => {
    const longName = "a".repeat(129);
    expect(() =>
      parsePostAuthFrame(
        JSON.stringify({ type: "watch", channel: longName, swarm: "s1", cursor: 0 })
      )
    ).toThrow(ProtocolError);
  });

  it("accepts channel name at exactly 128 chars", () => {
    const name128 = "a".repeat(128);
    const frame = parsePostAuthFrame(
      JSON.stringify({ type: "watch", channel: name128, swarm: "s1", cursor: 0 })
    );
    expect(frame.type).toBe("watch");
  });

  it("throws on negative cursor", () => {
    expect(() =>
      parsePostAuthFrame(
        JSON.stringify({ type: "watch", channel: "ch", swarm: "s1", cursor: -1 })
      )
    ).toThrow(ProtocolError);
  });

  it("throws on non-integer cursor", () => {
    expect(() =>
      parsePostAuthFrame(
        JSON.stringify({ type: "watch", channel: "ch", swarm: "s1", cursor: 1.5 })
      )
    ).toThrow(ProtocolError);
  });

  it("throws on empty body in send", () => {
    expect(() =>
      parsePostAuthFrame(
        JSON.stringify({ type: "send", channel: "ch", swarm: "s1", body: "" })
      )
    ).toThrow(ProtocolError);
  });

  it("throws on unknown frame type", () => {
    expect(() =>
      parsePostAuthFrame(JSON.stringify({ type: "unknown", swarm: "s1" }))
    ).toThrow(ProtocolError);
  });

  it("throws on invalid JSON", () => {
    expect(() => parsePostAuthFrame("{bad json")).toThrow(ProtocolError);
  });
});
