---
title: "Chunks: The Assignment That Becomes the Record"
status: DRAFTING
---

# Chunks: The Assignment That Becomes the Record

## Beat Outline

### The Struggle: Scoped Assignments Already Exist

#### Beat 1: Plan mode / Cursor already solved scoping
> Discovering plan mode in Cursor and in Cloud and as skills was a breakthrough for me. It made the scope of work I could reliably tackle with agents increase by easily a factor of three. And it became what I did all the time to do with the plan that resulted.

> The problem was, once the plan was implemented, all of that detail in the plan was now in the code. It was hard to justify committing it. But there's also stuff in the plan that had semantic value and reasoning, and I really wanted that stuff.

> So one of the first decisions I made when designing the Vibe engineering workflow is to split these two components into separate files. The "why" lives in a file I named "goal," and the "how" lives in a file I named "plan." I commit both of those to the repository in a way that makes them easily discoverable by agents.

> Because the goal is typically what an agent needs to learn the whole of something it's looking at, it tends to be the only file the agent bothers to read. But sometimes the agent needs to get into the weeds of the decision making, and it will refer to the plan.

> I don't force agents to consider the why and then the detailed how and the code to make a decision. This is one example of progressive disclosure. 

#### Beat 2: But when the session ends, reasoning evaporates
>

#### Beat 3: The next agent sees code but not *why*
>

#### Beat 4: You explain the same context again. And again.
> The beauty of retaining the why that I discover over and over again is you can refer back to it in prompts explicitly. You might say, "Hey, we're debugging what we did in this chunk," and then just reference the chunk, and you don't need to explain the setup again or how you got there or all the thinking that led to the change, or even what the scope of the change is, because all of that information is in the chunk.

> This is a huge unlock for quickly prompting a fresh agent to pick up from some work that a prior agent left behind. For picking up that work that encountered a bug in production that you only ever saw in production and you didn't get to see until three days later when the code was actually deployed. 

### The Insight: Assignment = Documentation

#### Beat 5: The chunk is both assignment AND medical record
> The act of creating a chunk is no more difficult than the act of creating a plan. We start with a rough direction of what we want to do, and a /command materializes a goal file from a template. The agent incorporates what it can of what you said into the goal, and for the additional things that it might need clarification on, it asks you questions until it gets to a very well-known refined goal file.

> Then another /command instructs the agent to complete a plan file from that goal. The plan file is another template that guides the agent through a workflow that I've found to be more likely to end in success and a strongly linked wiki. 

#### Beat 6: Same artifact serves both purposes
> So the end result is really you took two steps, but it was no more work. You defined the goal and then you refined it into a plan, really, the agent refined it into a plan. 

> Time elapsed relative to using cursor plan mode is the same. It makes no impact to how long it takes to accomplish something. But you end up with these two artifacts, both of which are evergreen, referred to in the future and committed to your repo and used by all future agents. 

#### Beat 7: Writing the GOAL.md to assign work IS writing documentation
>

#### Beat 8: No extra cost—you were going to scope the work anyway
>

### The Resolution: Compounding Wiki

#### Beat 9: Every chunk is a page in your onboarding wiki
>

#### Beat 10: You never have to explain that particular assignment again
>

#### Beat 11: Future agents discover chunks through code backreferences
>

#### Beat 12: One-time effort compounds into institutional memory
>

### The Key Tension Resolved

#### Beat 13: "Documentation feels like overhead" → "The assignment IS the documentation"
>

### Theme Connections (weave throughout, don't make explicit)

- **Amnesiac surgeon** — the chunk externalizes memory that would otherwise be lost
- **Discoverable documentation** — code links back to chunks; agents explore reasoning from anywhere
- **Compounding judgment** — chunks accumulate into a wiki that gets smarter over time

---

## Draft

### The Struggle

Discovering plan mode was a breakthrough for me. It made the scope of work I could reliably tackle with agents increase by easily a factor of three. And it became what I did all the time.

[? Beat 2-3: Gap—need voice on reasoning evaporating, next agent seeing code but not why]

The problem was, once the plan was implemented, all of that detail in the plan was now in the code. There's still some semantic value uniquely in the plan but it's surrounded by stuff we've now duplicated into the code which makes it hard to justify committing the plan.

So one of the first decisions I made when designing the vibe engineering workflow was to split these two components into separate files. The "why" lives in a file I named GOAL.md, and the "how" lives in a file I named PLAN.md. I commit both to the repository in a way that makes them easily discoverable by agents.

Because the goal is typically what an agent needs to learn the gestalt of something it's looking at, it tends to be the only file the agent bothers to read. But sometimes the agent needs to get into the weeds of the decision making, and it will refer to the plan. Because the agent is free to read only what it needs to understand it's next task we prevent overwhelm.

### The Insight

The act of creating a chunk is no more difficult than the act of creating a plan. We start by giving `/chunk-create` a rough direction of what we want to do. The agent uses a CLI to instantiate GOAL and PLAN templates and then folds your rough direction into the GOAL. The template guides the agent to explore the broader context and ask you clarifying questions about the intended outcome. When the command completes, you'll have a GOAL file that future agents will recognize and follow.

Then `/chunk-plan` instructs the agent to do a detailed implementation analysis given the code. The agent will fold its learnings into the PLAN template and add some forward references to the GOAL to the code that will help it finish up later.

Now, your planning process took two steps but required no additional work. You gained a distilled semantic understanding of the change that you can commit to used by all future agents.

[? Beat 7-8: Gap—need voice on "writing the goal IS writing documentation" / "no extra cost"]

### The Resolution

The beauty of retaining the why that I discover over and over again is you can refer back to it in prompts explicitly. You might say, "Hey, we're debugging what we did in this chunk," and then just reference the chunk. You don't need to explain the setup again or how you got there or all the thinking that led to the change, or even what the scope of the change is, because all of that information is in the chunk.

This is a huge unlock for quickly prompting a fresh agent to pick up work that a prior agent left behind. For picking up work that encountered a bug in production that you only ever saw in production and you didn't get to see until three days later when the code was actually deployed.

[? Beat 9-12: Gap—need voice on chunks as wiki pages, never explaining again, backreferences, compounding]

[? Beat 13: Gap—need voice on the key tension resolved: "Documentation feels like overhead" → "The assignment IS the documentation"]

---

## Parking Lot

(ideas cut for flow)
