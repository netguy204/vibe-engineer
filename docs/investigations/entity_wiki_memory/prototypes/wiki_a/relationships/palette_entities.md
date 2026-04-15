---
title: Palette Entities (Peers)
created: 2026-03-31
updated: 2026-03-31
---

# Palette Entities

Other entities in the palette as of the session. Five total including myself.

## Entities

| Entity | ID | Status | Subscribers | Notes |
|--------|----|--------|------------|-------|
| **Slack Watcher** | `58d36632-...` | awake | 1 (Data Load Status) | Publisher; I operated this entity in session 1 |
| **[[linear_ramp_tool\|Linear Ramp]]** | `ecbc0849-...` | awake | 1 (Ramp Bar Chart) | Continuous interpolation 1-10; I built and operated this in session 2 |
| **[[ramp_bar_chart]]** | `70440966-...` | awake | 0 | Consumes from Linear Ramp with `{"type":"all"}` filter |
| **[[data_load_status]]** | `ca7eeea2-...` | awake | 0 | Consumes from Slack Watcher |
| **Billing Tracker** | `e9ee8f4a-...` | processing | 0 | Appeared later in session 1 |

## Topology

```
Slack Watcher --> Data Load Status
Linear Ramp  --> Ramp Bar Chart
Billing Tracker (standalone)
```
