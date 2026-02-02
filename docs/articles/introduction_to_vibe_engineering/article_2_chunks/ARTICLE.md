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
> So the end result is really you took two steps (create and plan), but it was no more work. You defined the goal and then you asked the agent to refine it into a plan. However, these two steps pay off for you in a big way: you focused on the goal, where your judgment matters most... you got that sharp and correct with the help of an agent focused only on refining this chunk. Then a fresh agent studied your goal and the code (with its documented previous chunks and subsystems) and mapped out how to bring your GOAL into reality as a PLAN. When I'm introducing vibe engineering to a project (new or legacy) I'll typically review the first 3-6 PLANs to make sure the documentation environment is informative enough regarding my architectural vision. Then I stop reviewinng plans and rarely need to look back. I then create a fresh agent to implement the PLAN. Since the PLAN is exactly the codebase context needed to bring GOAL to life, this agent gets to use most of its working memory on just writing great code and useful tests.

> Time elapsed relative to using cursor plan mode is the same. It makes no impact to how long it takes to accomplish something. But you end up with these two artifacts, both of which are evergreen, referred to in the future and committed to your repo and used by all future agents. 

#### Beat 7: Writing the GOAL.md to assign work IS writing documentation
> But, unlike plan mode, since we've kept our focus on the why, we have an artifact that can responsibly persist in the repository to guide future agents.

#### Beat 8: No extra cost—you were going to scope the work anyway
>

### The Resolution: Compounding Wiki

#### Beat 9: Every chunk is a page in your onboarding wiki
> I think of the chunk GOALs in my project as a bunch of little tent-poles and stakes of judgment that help the massive patchwork tarp of code that my agents are spreading keep the desired shape. An agent working on one part of the tent can see the tent-poles and stakes that are relevant to their work without needing to worry about other sections of the tent.

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

Discovering plan mode was a breakthrough for me. Asking the agent to plan first easily tripled the scope of work that it could reliably complete. Plan first became what I did all the time and my confidence in agent-assisted coding soared.

But after the plan was implemented, I was faced with an unsatisfying decision: All of that reasoning was now "in the code" - but was it really? The plan and the chat session that created it had semantic value: *why* we made certain choices, *what* we considered and rejected, *how* the pieces fit together. The code captured the outcome, not the thinking. It felt wrong to throw the plan away, but hard to justify keeping it when so much had been duplicated.

I realized the plan was actually two things tangled together: the *why* (intent, constraints, decisions) and the *how* (implementation steps, file changes, execution order). The *how* becomes a bit redundant once the code exists. The *why* stays valuable forever — but only if future agents can find it.

So I split them. The "why" lives in a file I named GOAL.md. The "how" lives in PLAN.md. I commit both for each chunk of work that I define, but the GOAL is the one that matters long-term. It's what agents read to understand intent. The PLAN is there if they need implementation details, but most of the time they don't. (See sidebar: *How Agents Build Context*.)

### The Insight

The act of creating a chunk is no more difficult than the act of creating a plan. We start by giving `/chunk-create` a rough direction of what we want to do. The agent uses a CLI to instantiate GOAL and PLAN templates and then folds your rough direction into the GOAL. The template guides the agent to explore the broader context and ask you clarifying questions about the intended outcome. When the command completes, you'll have a GOAL file full of rich "why" and "why not" judgments that future agents will recognize and follow.

Then `/chunk-plan` instructs the agent to do a detailed implementation analysis given the code. This is where the agent does the deep exploration of the existing relevant code (and their backreferenced chunks) and builds exactly what the implementing agent will need to know to realize your vision while maintaining your previous judgments. The agent will fold its learnings into the PLAN template.

Now, your planning process was technically two steps but required no additional judgment. You gained a distilled semantic understanding of the change that you can commit to be used by all future agents, and you gained a PLAN that incorporated your judgments for this work and from earlier chunks.

Does this actually work? I analyzed 318 orchestrator transcripts to find out. (What's an orchestrator? A future article will cover that.)

The data tells two stories. First, *how often* agents follow backreferences depends on what phase they're in:

| Phase | Followthrough Rate |
|-------|-------------------|
| Plan | 62% |
| Complete | 39% |
| Review | 38% |
| Implement | 23% |

During planning, agents actively gather context — they follow most backreferences they encounter. By implementation, they're heads-down coding. The 23% rate might look low, but it's intentional: the PLAN already contains the context they need. Do your thinking in planning, do your coding in implementation.

Second, *what* agents read when they do follow:

| Pattern | Frequency |
|---------|-----------|
| GOAL.md only | 53% |
| Both files | 31% |
| PLAN.md only | 16% |

84% of follows include the GOAL — agents reach for the *why* first. The PLAN is there when they need implementation details, but most of the time they don't.

The two-file split isn't overhead. It's the natural structure agents already want.

### The Resolution

One advantage of retaining the *why* is you can refer back to it explicitly as you're prompting the next chunk of work. "Hey, we're debugging what we did in this chunk" — and you just reference the chunk. You don't need to explain the setup, how you got there, or what the scope was. All of that lives in the chunk.

This is a huge unlock for picking up work a prior agent left behind. Think about that bug in production that you didn't see until long after the agent session that created it was lost. The medical record is there. The next surgeon can prime itself by reading it.

But chunks do more than solve amnesia. They hold the shape.

I think of chunk GOALs as tent-poles and stakes. They are points of judgment that help the sprawling fabric of code keep its intended form. An agent working on one section of the tent can see the poles and stakes nearby without needing to understand the whole structure. They work locally, but aligned.

Every chunk you write is like another page in your onboarding wiki that you never have to explain again. Future agents discover it through backreferences in the code — they trace from implementation to intent, exploring as needed. They're not reading everything; they're finding relevant context when they need it. The wiki page is there when the agent needs its insights.

Your one-time effort compounds into institutional memory. As the tent gets bigger, it gets more poles and stakes. The shape holds, and everyone feels a little safer running around inside.

I didn't add documentation to my workflow. I just found a way to productively keep the documentation my prompting was creating around. The act of scoping the work *was* the act of documenting it. No extra cost. The overhead I'd always resisted turned out to be work I was already doing — I just wasn't saving it.

We've solved surgeon amnesia with workflow, not effort. Conveniently, the next generation of meat-based junior developers we bring into the codebase will assimilate our judgment through the same artifacts.

---

## Sidebar: How Agents Build Context

Agents are built on LLMs, and LLMs are stateless functions. All an LLM can use to generate its next response is the payload in the API request — there's no persistent memory between sessions.

This payload typically includes:
- **System prompt** — instructions from the agent developer (and things you provide via CLAUDE.md and skill definitions)
- **Conversation history** — the back-and-forth so far, including tool call results
- **The latest user message** — what you just asked

When you start a fresh session, conversation history is empty. The agent has only the system prompt to work with. But what distinguishes an agent from old-school ChatGPT is that agents can *build* their own context by exploring. They grep around, read files, and accumulate understanding through tool calls. Each result goes into conversation history, expanding what the agent knows.

This is all part of the emerging discipline of **context engineering** — designing what goes into that payload so agents arrive informed and stay focused.

The problem: if the agent's exploration finds only code, it won't understand the forces that shaped it. You end up with a surgeon obsessed with the symptoms but ignorant of the medical history. The end result is the agent does what you asked but also hallucinates worthless features, ignores architectural patterns, and reinvents things that already exist. It's operating brilliantly on what's there but without the intent that caused it to be there.

**How chunks help:** When agents explore, backreferences in the code point them to chunk GOALs. Instead of inferring intent from implementation, they can read it directly. The context they build includes *why*, not just *what*.

Here's a real example from this project's codebase:

```python
# Chunk: docs/chunks/symbolic_code_refs - Hierarchical containment check
def is_parent_of(parent: str, child: str) -> bool:
    # ... validation and file matching ...

    # Check if child's symbol starts with parent's symbol followed by ::
    # e.g., "Bar::baz" starts with "Bar::" making "Bar" a parent
    return child_symbol.startswith(parent_symbol + "::")
```

Without context, this looks like an arbitrary choice. Why `::` instead of `.`? Why string prefix matching instead of AST comparison?

The GOAL.md explains: the `::` separator was chosen specifically so overlap detection between chunks can work through simple string operations. If chunk A references `foo.py#Bar` and chunk B references `foo.py#Bar::baz`, containment is computable via `startswith()` — no parsing required.

The agent reading this code now understands the design force behind it. The choice isn't arbitrary; it's load-bearing.

---

## Parking Lot

(ideas cut for flow)
