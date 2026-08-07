# Cursor plugin schemas — vendored fixtures

<!-- Chunk: docs/chunks/dualplugin_cursor_scaffold - Cursor manifests validated against the upstream spec -->

`plugin.schema.json` and `marketplace.schema.json` in this directory are
byte-identical copies of the official Cursor plugin schemas. They exist so
`tests/test_cursor_manifest.py` can validate this repository's
`.cursor-plugin/` manifests against the *actual* spec rather than against a
paraphrase of it in assertion form — the same check upstream's own CI runs
with Ajv in `scripts/validate-plugins.mjs`.

## Source

| | |
|---|---|
| Repository | <https://github.com/cursor/plugins> |
| Path | `schemas/plugin.schema.json`, `schemas/marketplace.schema.json` |
| Commit | `070189284e702e8a4d2e3cc8913994b204c5337a` (2026-08-04) |
| Fetched | 2026-08-07 |
| License | MIT (per the upstream repository) |

Raw URLs:

```
https://raw.githubusercontent.com/cursor/plugins/070189284e702e8a4d2e3cc8913994b204c5337a/schemas/plugin.schema.json
https://raw.githubusercontent.com/cursor/plugins/070189284e702e8a4d2e3cc8913994b204c5337a/schemas/marketplace.schema.json
```

SHA-256 of the vendored copies:

```
a393b758901803fcf5cfe0d77bda8a83e987d32c3377dfce2d9edf445af884ed  plugin.schema.json
1aae96a24c2796419933bc8bfe3a1255394e7199c35740b36325e0ce6dbc253d  marketplace.schema.json
```

## Refreshing

These are a snapshot and will go stale. To refresh, re-fetch both files from
`main`, update the commit/date/hashes above, and run
`uv run pytest tests/test_cursor_manifest.py`. A failure after a refresh is
the signal this fixture exists to produce: the spec moved and our manifests
have not.

Note that `additionalProperties: false` applies to both the plugin manifest
and its `author` object, so an upstream *addition* of a field we already use
under a different name would surface here as a validation error rather than
as silent tolerance.
