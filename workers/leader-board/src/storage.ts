// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Durable Object SQLite storage layer for the leader board.
 *
 * Mirrors the Python StorageAdapter protocol. Uses DO SQL storage
 * for the append-only message log and swarm metadata.
 */

export interface SwarmMeta {
  swarm_id: string;
  public_key: string; // hex-encoded Ed25519 public key
  created_at: string; // ISO 8601 UTC
}

export interface StoredMessage {
  channel: string;
  position: number;
  body: string;
  sent_at: string; // ISO 8601 UTC
}

export interface ChannelInfo {
  name: string;
  head_position: number;
  oldest_position: number;
}

export class SwarmStorage {
  private sql: DurableObjectStorage;
  private initialized = false;

  constructor(storage: DurableObjectStorage) {
    this.sql = storage;
  }

  private ensureSchema(): void {
    if (this.initialized) return;

    this.sql.sql.exec(`
      CREATE TABLE IF NOT EXISTS swarm_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )
    `);

    this.sql.sql.exec(`
      CREATE TABLE IF NOT EXISTS messages (
        channel TEXT NOT NULL,
        position INTEGER NOT NULL,
        body TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        PRIMARY KEY (channel, position)
      )
    `);

    // Index for efficient range reads and compaction
    this.sql.sql.exec(`
      CREATE INDEX IF NOT EXISTS idx_messages_channel_position
        ON messages(channel, position)
    `);

    // Chunk: docs/chunks/gateway_token_storage - Gateway key blob storage
    this.sql.sql.exec(`
      CREATE TABLE IF NOT EXISTS gateway_keys (
        token_hash TEXT PRIMARY KEY,
        encrypted_blob TEXT NOT NULL,
        created_at TEXT NOT NULL
      )
    `);

    // Chunk: docs/chunks/invite_instruction_page - Add swarm_id for invite token routing
    try {
      this.sql.sql.exec(
        `ALTER TABLE gateway_keys ADD COLUMN swarm_id TEXT NOT NULL DEFAULT ''`
      );
    } catch {
      // Column may already exist — safe to ignore
    }

    this.initialized = true;
  }

  // --- Swarm Operations ---

  saveSwarm(swarmId: string, publicKeyHex: string): void {
    this.ensureSchema();
    const now = new Date().toISOString();

    this.sql.sql.exec(
      `INSERT OR REPLACE INTO swarm_meta (key, value) VALUES (?, ?)`,
      "public_key",
      publicKeyHex
    );
    this.sql.sql.exec(
      `INSERT OR REPLACE INTO swarm_meta (key, value) VALUES (?, ?)`,
      "created_at",
      now
    );
    this.sql.sql.exec(
      `INSERT OR REPLACE INTO swarm_meta (key, value) VALUES (?, ?)`,
      "swarm_id",
      swarmId
    );
  }

  getSwarm(): SwarmMeta | null {
    this.ensureSchema();

    const rows = [...this.sql.sql.exec(`SELECT key, value FROM swarm_meta`)];
    if (rows.length === 0) return null;

    const meta: Record<string, string> = {};
    for (const row of rows) {
      meta[row.key as string] = row.value as string;
    }

    if (!meta.public_key || !meta.created_at || !meta.swarm_id) return null;

    return {
      swarm_id: meta.swarm_id,
      public_key: meta.public_key,
      created_at: meta.created_at,
    };
  }

  // --- Message Operations ---

  appendMessage(channel: string, body: string): { position: number; sent_at: string } {
    this.ensureSchema();

    // Get next position (MAX + 1, or 1 if empty)
    // DOs are single-threaded, so this is safe without explicit locking
    const maxRows = [
      ...this.sql.sql.exec(
        `SELECT COALESCE(MAX(position), 0) as max_pos FROM messages WHERE channel = ?`,
        channel
      ),
    ];
    const maxPos = (maxRows[0]?.max_pos as number) ?? 0;
    const position = maxPos + 1;
    const sentAt = new Date().toISOString();

    this.sql.sql.exec(
      `INSERT INTO messages (channel, position, body, sent_at) VALUES (?, ?, ?, ?)`,
      channel,
      position,
      body,
      sentAt
    );

    return { position, sent_at: sentAt };
  }

  readAfter(channel: string, cursor: number): StoredMessage | null {
    this.ensureSchema();

    const rows = [
      ...this.sql.sql.exec(
        `SELECT channel, position, body, sent_at FROM messages
         WHERE channel = ? AND position > ?
         ORDER BY position ASC LIMIT 1`,
        channel,
        cursor
      ),
    ];

    if (rows.length === 0) return null;

    const row = rows[0];
    return {
      channel: row.channel as string,
      position: row.position as number,
      body: row.body as string,
      sent_at: row.sent_at as string,
    };
  }

  // Chunk: docs/chunks/gateway_cleartext_api - Batch read for cleartext gateway
  readAfterBatch(channel: string, cursor: number, limit: number = 50): StoredMessage[] {
    this.ensureSchema();

    const rows = [
      ...this.sql.sql.exec(
        `SELECT channel, position, body, sent_at FROM messages
         WHERE channel = ? AND position > ?
         ORDER BY position ASC LIMIT ?`,
        channel,
        cursor,
        limit
      ),
    ];

    return rows.map((row) => ({
      channel: row.channel as string,
      position: row.position as number,
      body: row.body as string,
      sent_at: row.sent_at as string,
    }));
  }

  listChannels(): ChannelInfo[] {
    this.ensureSchema();

    const rows = [
      ...this.sql.sql.exec(
        `SELECT channel, MAX(position) as head_position, MIN(position) as oldest_position
         FROM messages GROUP BY channel ORDER BY channel`
      ),
    ];

    return rows.map((row) => ({
      name: row.channel as string,
      head_position: row.head_position as number,
      oldest_position: row.oldest_position as number,
    }));
  }

  getChannelInfo(channel: string): ChannelInfo | null {
    this.ensureSchema();

    const rows = [
      ...this.sql.sql.exec(
        `SELECT MAX(position) as head_position, MIN(position) as oldest_position
         FROM messages WHERE channel = ?`,
        channel
      ),
    ];

    if (rows.length === 0 || rows[0].head_position === null) return null;

    return {
      name: channel,
      head_position: rows[0].head_position as number,
      oldest_position: rows[0].oldest_position as number,
    };
  }

  /**
   * Remove messages older than minAgeDays, always retaining the most recent message.
   * Returns the count of deleted rows.
   */
  compact(channel: string, minAgeDays: number): number {
    this.ensureSchema();

    const cutoff = new Date(Date.now() - minAgeDays * 24 * 60 * 60 * 1000).toISOString();

    // Find the max position so we can always retain it
    const maxRows = [
      ...this.sql.sql.exec(
        `SELECT MAX(position) as max_pos FROM messages WHERE channel = ?`,
        channel
      ),
    ];
    const maxPos = maxRows[0]?.max_pos as number | null;
    if (maxPos === null) return 0; // no messages to compact

    // Delete old messages, but never the most recent
    const beforeCount = [
      ...this.sql.sql.exec(`SELECT COUNT(*) as cnt FROM messages WHERE channel = ?`, channel),
    ];

    this.sql.sql.exec(
      `DELETE FROM messages WHERE channel = ? AND sent_at < ? AND position < ?`,
      channel,
      cutoff,
      maxPos
    );

    const afterCount = [
      ...this.sql.sql.exec(`SELECT COUNT(*) as cnt FROM messages WHERE channel = ?`, channel),
    ];

    return (beforeCount[0].cnt as number) - (afterCount[0].cnt as number);
  }

  // --- Gateway Key Operations ---

  // Chunk: docs/chunks/gateway_token_storage - Store encrypted key blob
  // Chunk: docs/chunks/invite_instruction_page - Added swarm_id parameter
  putGatewayKey(tokenHash: string, encryptedBlob: string, swarmId: string = ""): void {
    this.ensureSchema();
    const now = new Date().toISOString();
    this.sql.sql.exec(
      `INSERT OR REPLACE INTO gateway_keys (token_hash, encrypted_blob, created_at, swarm_id) VALUES (?, ?, ?, ?)`,
      tokenHash,
      encryptedBlob,
      now,
      swarmId
    );
  }

  // Chunk: docs/chunks/gateway_token_storage - Retrieve encrypted key blob
  // Chunk: docs/chunks/invite_instruction_page - Added swarm_id to return type
  getGatewayKey(
    tokenHash: string
  ): { token_hash: string; encrypted_blob: string; created_at: string; swarm_id: string } | null {
    this.ensureSchema();
    const rows = [
      ...this.sql.sql.exec(
        `SELECT token_hash, encrypted_blob, created_at, swarm_id FROM gateway_keys WHERE token_hash = ?`,
        tokenHash
      ),
    ];
    if (rows.length === 0) return null;
    const row = rows[0];
    return {
      token_hash: row.token_hash as string,
      encrypted_blob: row.encrypted_blob as string,
      created_at: row.created_at as string,
      swarm_id: row.swarm_id as string,
    };
  }

  // Chunk: docs/chunks/gateway_token_storage - Delete encrypted key blob (revocation)
  deleteGatewayKey(tokenHash: string): boolean {
    this.ensureSchema();
    const beforeRows = [
      ...this.sql.sql.exec(
        `SELECT COUNT(*) as cnt FROM gateway_keys WHERE token_hash = ?`,
        tokenHash
      ),
    ];
    const beforeCount = beforeRows[0].cnt as number;
    if (beforeCount === 0) return false;

    this.sql.sql.exec(
      `DELETE FROM gateway_keys WHERE token_hash = ?`,
      tokenHash
    );
    return true;
  }

  // Chunk: docs/chunks/invite_list_revoke - List all gateway keys
  listGatewayKeys(): { token_hash: string; created_at: string }[] {
    this.ensureSchema();
    const rows = [
      ...this.sql.sql.exec(
        `SELECT token_hash, created_at FROM gateway_keys ORDER BY created_at ASC`
      ),
    ];
    return rows.map((row) => ({
      token_hash: row.token_hash as string,
      created_at: row.created_at as string,
    }));
  }

  // Chunk: docs/chunks/invite_list_revoke - Delete all gateway keys (bulk revocation)
  deleteAllGatewayKeys(): number {
    this.ensureSchema();
    const countRows = [
      ...this.sql.sql.exec(`SELECT COUNT(*) as cnt FROM gateway_keys`),
    ];
    const count = countRows[0].cnt as number;
    if (count === 0) return 0;
    this.sql.sql.exec(`DELETE FROM gateway_keys`);
    return count;
  }
}
