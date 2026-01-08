# Specification

<!--
This document is the contract. It defines WHAT the system does with enough
precision that you could write a conformance test suite against it.

The spec can evolve, but changes should be deliberate. When you modify this
document, consider what downstream artifacts (chunks, implementations, tests)
need to be updated.

Mark sections as DRAFT if they're not yet solidified.
-->

## Overview

<!--
A brief summary of what this specification defines. One or two paragraphs
that orient the reader before diving into details.
-->

## Terminology

<!--
Define terms that have specific meanings in this project. This prevents
ambiguity and ensures everyone (including agents) uses language consistently.

Example:
- **Message**: A single unit of data written to the queue
- **Segment**: A file containing a sequence of messages
- **Acknowledgment**: Confirmation that a message has been processed
-->

## Data Format

<!--
If the system has a persistent representation (file format, wire protocol,
database schema), define it precisely here.

Include:
- Layout and structure
- Field definitions with types and valid ranges
- Encoding details (endianness, string encoding, etc.)
- Versioning scheme
- Checksums or integrity mechanisms

Be precise enough that someone could implement a parser from this description.
-->

## API Surface

<!--
Define the operations the system supports. For each operation:
- Name and signature
- Preconditions (what must be true before calling)
- Postconditions (what will be true after calling)
- Error conditions and how they're signaled
- Concurrency semantics (thread-safe? blocking? async?)

Example:
### write(message: bytes) -> MessageId
Appends a message to the queue.
- Preconditions: message.length > 0, message.length <= MAX_MESSAGE_SIZE
- Postconditions: message is durably stored, MessageId is unique
- Errors: QueueFull, MessageTooLarge, IOError
- Concurrency: Thread-safe, may block during fsync
-->

## Guarantees

<!--
What properties does the system guarantee? Be precise about conditions.

Examples:
- Durability: "A message is durable once write() returns. Durable means
  the message will survive process crash and OS crash, assuming no
  storage hardware failure."
- Ordering: "Messages are read in the order they were written within
  a single segment. Cross-segment ordering requires..."
- Delivery: "Each message will be delivered at least once. Exactly-once
  requires external deduplication."

Also specify what is NOT guaranteed if it might be assumed.
-->

## Performance Requirements

<!--
Quantitative requirements that implementations must meet.

Examples:
- Throughput: >= 50,000 messages/second for 1KB messages
- Latency: P99 write latency <= 10ms
- Space: Overhead per message <= 32 bytes
- Recovery: Queue must be readable within 5 seconds of process start

Specify measurement conditions (hardware class, message size, queue depth).
-->

## Limits

<!--
Hard limits that define the boundaries of correct operation.

Examples:
- Maximum message size: 16 MB
- Maximum messages per segment: 1,000,000
- Maximum queue depth: Limited by available disk space
- Maximum concurrent readers: 64

Specify what happens when limits are exceeded (error, undefined behavior, etc.)
-->

## Versioning and Compatibility

<!--
How does the spec evolve over time?
- How are versions identified?
- What compatibility guarantees exist between versions?
- How should implementations handle unknown versions?
-->

## DRAFT Sections

### Commands

#### ve init

Create the initial trunk document set from templates. Also initialize CLAUDE.md
and. cloud/commands from the templates. In its /command form, this may
investigate an existing code base and attempt to complete the goal and spec
documents within the trunk. Ultimately, the trunk documents are where a lot of
the engineering happens. So we can't eliminate the cost of init, but maybe we
can amortize it over a long period. 

#### ve chunk start <ticket>

Create a new chunk from the templates for the provided ticket number. The
initial status of the chunk is implementing. 

#### ve chunk finish

Mark the implementation of the chunk as complete and verify that grass
references are set. If all gates are met, set the status of the chunk to active. 

#### ve chunk abandon

If a chunk is in the implementing state, verify with the user and delete the
chunk with its documentation. If the chunk is in the active state, then change
the state to historic. 

#### ve vacuum

For all active chunks. 

```
grep -l "status: ACTIVE" docs/chunks/*/GOAL.md
```

For all code_paths and code_references in those chunks. 

```
git log --oneline --since="2024-01-01" -- src/segment/compactor.rs
```

Decide if the chunk was materially impacted by the changes, and ask the user
whether it should be updated or marked historic because drift has moved beyond
its intent. 