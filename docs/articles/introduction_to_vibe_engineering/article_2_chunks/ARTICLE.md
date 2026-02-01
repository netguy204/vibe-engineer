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
> Agents are built on LLMs and LLMs are stateless functions. All they can can use to generate their next completion is payload in the API request. This payload includes whatever the agent developer chose to send it (via a developing science known as context engineering)... but it's typically the conversation history (which includes the output from prior agent tool calls), the contents of CLAUDE.md (or AGENTS.md or whatever), and some metadata about available tools and skills. When you start a new session, conversation history is empty so all there is is the CLAUDE.md equivalent. Fortunately, when you ask for something, the agent can start exploring autonomously and buid up context in conversation history itself via tool calls. 

#### Beat 3: The next agent sees code but not *why*
> If all this exploration (starting with CLAUDE.md and maybe a few grep calls) finds only code then the agent won't understand the forces of intent that caused the code. Some symptoms that this is happening is the agent doing what you said but inventing worthless features along the way or ignoring architectural patterns or reinventing things that already existed.

#### Beat 4: You explain the same context again. And again.
> The beauty of retaining the why that I discover over and over again is you can refer back to it in prompts explicitly. You might say, "Hey, we're debugging what we did in this chunk," and then just reference the chunk, and you don't need to explain the setup again or how you got there or all the thinking that led to the change, or even what the scope of the change is, because all of that information is in the chunk.

> This is a huge unlock for quickly prompting a fresh agent to pick up from some work that a prior agent left behind. For picking up that work that encountered a bug in production that you only ever saw in production and you didn't get to see until three days later when the code was actually deployed. 

### The Insight: Assignment = Documentation

#### Beat 5: The chunk is both assignment AND medical record
> The act of creating a chunk is no more difficult than the act of creating a plan. We start with a rough direction of what we want to do, and a /command materializes a goal file from a template. The agent incorporates what it can of what you said into the goal, and for the additional things that it might need clarification on, it asks you questions until it gets to a very well-known refined goal file.

> Then another /command instructs the agent to complete a plan file from that goal. The plan file is another template that guides the agent through a workflow that I've found to be more likely to end in success and a strongly linked wiki. 

#### Beat 6: Same artifact serves both purposes
> So the end result is really you took two steps (create and plan), but it was no more work. You defined the goal and then you asked the agent to refine it into a plan. However, these two steps pay off for you in a big way: you focused on the goal, where your judgement matters most... you got that sharp and correct with the help of an agent focused only on refining this chunk. Then a fresh agent studied your goal and the code (with its documented previous chunks and subsystems) and mapped out how to bring your GOAL into reality as a PLAN. When I'm introducing vibe engineering to a project (new or legacy) I'll typically review the first 3-6 PLANs to make sure the documentation environment is informative enough regarding my architectural vision. Then I stop reviewinng plans and rarely need to look back. I then create a fresh agent to implement the PLAN. Since the PLAN is exactly the codebase context needed to bring GOAL to life, this agent gets to use most of its working memory on just writing great code and useful tests.

> Time elapsed relative to using cursor plan mode is the same. It makes no impact to how long it takes to accomplish something. But you end up with these two artifacts, both of which are evergreen, referred to in the future and committed to your repo and used by all future agents. 

#### Beat 7: Writing the GOAL.md to assign work IS writing documentation
> But, unlike plan mode, since we've kept our focus on the why, we have an artifact that can responsibly persist in the repository to guide future agents.

#### Beat 8: No extra cost—you were going to scope the work anyway
>

### The Resolution: Compounding Wiki

#### Beat 9: Every chunk is a page in your onboarding wiki
> I think of the chunk GOALs in my project as a bunch of little tent-poles and stakes of judgement that help the massive patchwork tarp of code that my agents are spreading keep the desired shape. An agent working on one part of the tent can see the tent-poles and stakes that are relevant to their work without needing to worry about other sections of the tent.

#### Beat 10: You never have to explain that particular assignment again
>

#### Beat 11: Future agents discover chunks through code backreferences
>  (let's figure out how to incorporate the findings.md research results here)

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

But here's the thing about agents: they're stateless. Every session starts empty. The agent can explore — grep around, read files, build up context — but if that exploration finds only code, it won't understand the forces that shaped it. You'll see the symptoms: the agent does what you asked but invents worthless features along the way, ignores architectural patterns, reinvents things that already exist. It's operating without intent.

The problem was, once the plan was implemented, all of that detail in the plan was now in the code. There's still some semantic value uniquely in the plan but it's surrounded by stuff we've now duplicated into the code which makes it hard to justify committing the plan.

So one of the first decisions I made when designing the vibe engineering workflow was to split these two components into separate files. The "why" lives in a file I named GOAL.md, and the "how" lives in a file I named PLAN.md. I commit both to the repository in a way that makes them easily discoverable by agents.

Because the goal is typically what an agent needs to learn the gestalt of something it's looking at, it tends to be the only file the agent bothers to read. But sometimes the agent needs to get into the weeds of the decision making, and it will refer to the plan. Because the agent is free to read only what it needs to understand it's next task we prevent overwhelm.

### The Insight

The act of creating a chunk is no more difficult than the act of creating a plan. We start by giving `/chunk-create` a rough direction of what we want to do. The agent uses a CLI to instantiate GOAL and PLAN templates and then folds your rough direction into the GOAL. The template guides the agent to explore the broader context and ask you clarifying questions about the intended outcome. When the command completes, you'll have a GOAL file that future agents will recognize and follow.

Then `/chunk-plan` instructs the agent to do a detailed implementation analysis given the code. The agent will fold its learnings into the PLAN template and add some forward references to the GOAL to the code that will help it finish up later.

Now, your planning process took two steps but required no additional work. You gained a distilled semantic understanding of the change that you can commit to used by all future agents.

Does this actually work? I analyzed 318 orchestrator transcripts to find out. When agents encounter a backreference and choose to follow it, they read:

| Pattern | Frequency |
|---------|-----------|
| GOAL.md only | 53% |
| GOAL first, then PLAN | 26% |
| PLAN.md only | 16% |

84% of the time, agents read the GOAL — the *why* — either alone or before consulting the PLAN. During implementation, that jumps to 70% GOAL-only. The agent grabs the intent and moves on. During planning and review, they're more exploratory and consult both files.

The two-file split isn't overhead. It's the natural structure agents already want.

### The Resolution

The beauty of retaining the *why* is you can refer back to it explicitly. "Hey, we're debugging what we did in this chunk" — and you just reference the chunk. You don't need to explain the setup, how you got there, or what the scope was. All of that lives in the chunk.

This is a huge unlock for picking up work a prior agent left behind. For that bug in production you didn't see until three days later when the code was finally deployed. The medical record is there. The next surgeon reads it.

But chunks do more than solve amnesia. They hold the shape.

I think of chunk GOALs as tent-poles and stakes — points of judgment that help the sprawling fabric of code keep its intended form. An agent working on one section of the tent can see the poles and stakes nearby without needing to understand the whole structure. They work locally, but aligned.

Every chunk you write is a page in your onboarding wiki that you never have to explain again. Future agents discover it through backreferences in the code — they trace from implementation to intent, exploring as needed. They follow backreferences about 18-35% of the time, and that's healthy. They're not reading everything; they're finding relevant context when they need it. The tent-poles are there when the agent reaches for them.

Your one-time effort compounds into institutional memory. The tent gets more stakes. The shape holds better.

And here's what I keep coming back to: I didn't add documentation to my workflow. I just kept the assignment around. The act of scoping the work *was* the act of documenting it. No extra cost. The overhead I'd always resisted turned out to be work I was already doing — I just wasn't saving it.

---

## Parking Lot

(ideas cut for flow)
