// Chunk: docs/chunks/leader_board_durable_objects - Cloudflare DO adapter
/**
 * Worker entry point — routes WebSocket connections to the correct SwarmDO.
 *
 * The Worker itself does no auth or protocol handling; it's a pure router.
 * The swarm query parameter is required for all connections (the client
 * knows its swarm ID at connection time since it derives from the public key).
 */

import { SwarmDO } from "./swarm-do";
import type { Env } from "./swarm-do";

export { SwarmDO };

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const swarmId = url.searchParams.get("swarm");

    if (!swarmId) {
      return new Response(
        JSON.stringify({ error: "Missing required 'swarm' query parameter" }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Route to the correct Durable Object by swarm ID
    const id = env.SWARM_DO.idFromName(swarmId);
    const stub = env.SWARM_DO.get(id);

    // Chunk: docs/chunks/gateway_token_storage - Route gateway key requests as plain HTTP
    if (url.pathname.startsWith("/gateway/keys")) {
      return stub.fetch(request);
    }

    // Chunk: docs/chunks/gateway_cleartext_api - Route cleartext gateway API requests
    if (url.pathname.match(/^\/gateway\/[^/]+\/channels\//)) {
      return stub.fetch(request);
    }

    // Only forward WebSocket upgrade requests to the DO
    const upgradeHeader = request.headers.get("Upgrade");
    if (!upgradeHeader || upgradeHeader.toLowerCase() !== "websocket") {
      return new Response("Expected WebSocket upgrade", { status: 426 });
    }

    return stub.fetch(request);
  },
};
