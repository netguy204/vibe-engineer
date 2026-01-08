Update the code references in the goal file of a chunk. 

The user has requested that the following chunk have its code references refreshed:

$ARGUMENTS

---

1. Identify the code references for the goal in the code_references field in the
   metadata of <chunk dir>/GOAL.md

2. Examine the code at the reference locations and determine if the references
   are still accurate. 

3. If a reference is not accurate, attempt to update it. You can search the code
   base for a chunk of code that is semantically capturing the intent of what
   the original reference targeted. You can examine later chunks to understand
   how and why the code that is being referenced may have changed and may no
   longer be referenceable. You can examine git history to understand where the
   referenced semantic concepts may have gone or why it may no longer exist.
   Take special note of any semantic concepts that no longer exist.

4. If all of the referenced locations either are unchanged or can be updated
   unambiguously to a new block of code that is the same semantic concept, then
   perform the update and respond to the user with a table summarizing the
   nature of your update. If any reference to a location is now obsolete because
   it semantically no longer exists or the most similar concept to map it to an
   ambiguous match. Describe the ambiguity or the absence to the user and ask
   them if they want to move the goal to the historical status. 