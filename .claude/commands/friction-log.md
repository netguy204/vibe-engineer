---
description: Capture a friction point for later pattern analysis
---




<!--
AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY

This file is rendered from: src/templates/commands/friction-log.md.jinja2
Edit the source template, then run `ve init` to regenerate.
-->



## Instructions

Capture a friction point quickly—something that slowed you down, confused you, or felt harder than it should be.


### If the operator provided an observation:

$ARGUMENTS

1. **Extract the friction** from their observation:
   - Title: A brief summary (under 10 words)
   - Description: What happened and why it was frustrating
   - Impact: low | medium | high | blocking

2. **Determine theme**: Read `docs/trunk/FRICTION.md` to see existing themes.
   Pick the best fit, or propose a new theme-id if none apply.

3. **Log the entry** non-interactively:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <theme-id>
   ```
   For an existing theme, use its theme-id. For a new theme, also provide --theme-name:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <new-theme-id> --theme-name "<Theme Display Name>"
   ```

4. **Confirm**: Tell the operator the entry ID that was created.

---

### If no observation was provided ($ARGUMENTS is empty):

Interview the operator with these questions:

1. > "What slowed you down or felt frustrating?"

2. > "How much did this impact your work? (low / medium / high / blocking)"

3. Read `docs/trunk/FRICTION.md` to see existing themes, then ask:
   > "Which theme fits best? [list existing themes] Or describe a new one."

4. **Log the entry** non-interactively using their answers:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <theme-id>
   ```
   For a new theme, also provide --theme-name:
   ```
   ve friction log --title "<title>" --description "<description>" --impact <impact> --theme <new-theme-id> --theme-name "<Theme Display Name>"
   ```

5. **Confirm**: Tell the operator the entry ID that was created.
