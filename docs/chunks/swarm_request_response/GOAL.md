---
status: ACTIVE
ticket: null
parent_chunk: null
code_paths:
- src/templates/commands/swarm-request-response.md.jinja2
- src/templates/claude/CLAUDE.md.jinja2
code_references:
- ref: src/templates/commands/swarm-request-response.md.jinja2
  implements: "Full request-response lifecycle skill template: argument parsing, cursor advance, background watch, request send, response filtering, and key concepts documentation"
- ref: src/templates/claude/CLAUDE.md.jinja2
  implements: "Registration of /swarm-request-response skill in the Available Commands section"
narrative: null
investigation: null
subsystems: []
friction_entries: []
bug_type: null
depends_on: []
created_after:
- board_channel_delete
- board_watch_offset
- board_watch_safety
- orchestrator_monitor_skill
---
# Chunk Goal

## Minor Goal

Create a new `/swarm-request-response` slash command skill that encapsulates the request-response pattern over swarm channel pairs.

The swarm's channel model is fire-and-forget: you send a message and watch for responses. But many agent workflows need request-response semantics — send a request to a steward and wait for a specific response on its changelog. The efficient way to do this is:

1. **Advance the response channel cursor to head** — query `ve board channels` to get the current message count, then set the cursor so the watch starts from the present moment, skipping all historical noise
2. **Start watching the response channel in the background** — `ve board watch <response-channel>` with `run_in_background`, so it's ready to receive before the request is even sent
3. **Send the request** — `ve board send <request-channel> "<message>"`
4. **Receive and filter** — when the background watch returns a message, the agent must use discernment to determine if it's actually a response to their request. The changelog is a broadcast channel — it may contain notifications from other requests. If the message isn't relevant, ack it and re-watch. If it is, process it and continue.

The most common channel pair is `<project>-steward` (request) / `<project>-changelog` (response). But the pattern is general — any two channels can form a request-response pair.

The skill should accept arguments for: request channel, response channel, request message body, and swarm ID. It should handle the full lifecycle: cursor advance, background watch setup, request send, response filtering, and return of the relevant response to the caller.

## Success Criteria

- `/swarm-request-response` skill exists in the commands directory
- Skill advances response channel cursor to head before watching
- Skill starts background watch on response channel before sending request (prevents race)
- Skill sends the request to the request channel
- Skill filters incoming responses for relevance to the original request
- Irrelevant responses are acked and the watch is restarted
- Relevant response is returned to the calling context
- Skill is registered in CLAUDE.md
- Documentation explains the pattern, the steward/changelog channel pair convention, and why ordering (watch before send) matters

