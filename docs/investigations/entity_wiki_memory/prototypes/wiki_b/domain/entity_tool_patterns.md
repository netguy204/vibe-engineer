---
title: Entity Tool Patterns
created: 2026-03-31
updated: 2026-03-31
---

# Entity Tool Patterns

## Proven Boilerplate (from consume.js)
Every mechanical tool should follow this exact structure:

```javascript
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const entityDir = process.env.PALETTE_ENTITY_DIR || path.resolve(__dirname, '..');
const entityId = process.env.PALETTE_ENTITY_ID || path.basename(entityDir);
const platformUrl = process.env.PALETTE_PLATFORM_URL || 'http://localhost:3001';
```

### Heartbeat Pattern
```javascript
function heartbeat() {
  try {
    const dir = path.join(entityDir, '.heartbeat');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'toolname.js'), String(Date.now()));
  } catch {}
}

// Background interval — runs regardless of main loop state
setInterval(heartbeat, 5000);
```

### Main Loop Pattern
```javascript
async function main() {
  heartbeat(); // immediate heartbeat before any async work
  // ... tool logic ...
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
```

### Signal Handlers
Required for Proving to work — tool runner sends SIGTERM to stop:
```javascript
process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));
```

## Anti-Patterns
- **No env var fallback**: `process.env.PALETTE_ENTITY_DIR` alone fails during some execution contexts
- **Inline-only heartbeat**: If the main loop blocks (network call, slow I/O), heartbeat stops
- **No fetch timeout**: `fetch()` without `AbortController` can hang indefinitely
- **Catching process exit non-zero on SIGTERM**: Default Node behavior exits non-zero on signals

## Relationship to [[palette_platform]]
Tools run inside the tool runner's process supervisor. See [[palette_platform#Proving State]] for lifecycle details.
