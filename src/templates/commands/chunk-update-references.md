Update the code references in the goal file of a chunk.

The operator has requested that the following chunk have its code references refreshed:

$ARGUMENTS

---

## Symbolic Reference Format

Code references use symbolic references in the format `{file_path}#{symbol_path}`:
- `src/chunks.py#Chunks` - reference to a class
- `src/chunks.py#Chunks::create_chunk` - reference to a method
- `src/ve.py#validate_short_name` - reference to a standalone function
- `src/models.py` - reference to an entire module (no symbol)

The `::` separator indicates nesting (class::method, outer::inner::method).

---

1. Identify the code references for the goal in the code_references field in the
   metadata of <chunk dir>/GOAL.md. References use the symbolic format above.

2. Examine the code at the reference locations and determine if the references
   are still accurate. For symbolic references, verify:
   - The file still exists
   - The symbol (class, function, method) still exists at the given path
   - The code still implements what the `implements` field describes

3. If a reference is not accurate, attempt to update it:
   - If a symbol was renamed, update the symbol path
   - If a symbol was moved to a different file, update the file path
   - If a symbol was moved within a class hierarchy, update the nesting path
   - Search the codebase for code semantically capturing the original intent
   - Examine later chunks and git history to understand changes

4. If all referenced symbols either still exist or can be updated unambiguously
   to a new symbol that represents the same semantic concept, perform the update
   and respond to the operator with a table summarizing the changes.

   If any reference is now obsolete (symbol deleted, concept no longer exists)
   or the best match is ambiguous, describe the situation to the operator and
   ask if they want to move the goal to HISTORICAL status. 