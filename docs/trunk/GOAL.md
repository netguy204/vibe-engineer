# Project Goal

The purpose of the Vibe-Engineer project is to support easy consitent
implementation of the vibe engineering workflow. 

The central thesis of the vibe engineering workflow is that a strong
documentation workflow leads to confident implementation of code and makes
future change relatively low cost. 


## Problem Statement

Creating a workflow that strikes a balance between implementation and
maintaining useful documentation has been an open problem of software
engineering since the beginning. A lot of the heart of this problem came from
the cost of maintaining the documentation and how it traded against the
implementation of the goal of the project.

This equation has changed in the last two years since implementation is now
effectively free via agentic systems, and deeply understanding the goal and the
correctness constraints around the project are the entire engineering problem
that remains. 


## Required Properties

The tooling that supports this workflow must remain effective even if not every
engineer working in the project uses the workflow. 

It must be possible to retrofit a legacy project into the workflow. 

It must be possible to perform the workflow outside the context of a Git
repository. 

Following the workflow must maintain the health of documents over time and
should not grow more difficult over time.  

Maintaining the referential integrity of documents is an agent problem. 

Deciding if a document is still relevant is an agent-supported human problem. 

Documents are never deleted, but they are superseded or noted as archaeological
points of interest. 

## Constraints

The artifacts produced by the workflow must be comprehensible and valuable to
humans and agents.



## Out of Scope

This is not an attempt to automate the engineering process. It's an attempt to
codify what remains the most valuable part of the engineering process, so that
modern agents are unlocked to do the rest. 

## Success Criteria

If a valuable workflow is created and supported by this tool, then it will be
obviously worthwhile to an engineer to spend the time writing the documents
required by the workflow, and maintaining those documents as the project
evolves. 