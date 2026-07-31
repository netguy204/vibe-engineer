Discovering “plan mode” was a breakthrough for me. Asking the agent to plan first easily tripled the scope of work that it could reliably complete. Plan first became what I did all the time, and my confidence in agent-assisted coding soared.
But after the agent implemented the plan, I was faced with an unsatisfying decision: All of that reasoning was now “in the code” - but was it really? The plan and the chat session that created it had semantic value: why we made particular choices, what we considered and rejected, and how the pieces fit together. The code captured the outcome, not the thinking. It felt wrong to throw the plan away, but it was hard to justify keeping it when so much had been duplicated.
I realized the plan was actually two things tangled together.
The why (intent, constraints, decisions) and the how (implementation steps, file changes, execution order). The how becomes a bit redundant once the code exists. The why stays valuable forever, but only if future agents can find it.
So I split them. The “why” lives in a file I named GOAL.md. The “how” lives in PLAN.md. I commit both files for each chunk of work I define, but the GOAL is what matters in the long term. It’s what agents read to understand intent. The PLAN is there if they need implementation details, but most of the time, they don’t. (See sidebar: How Agents Build Context.)
These "chunks" are the foundation of the vibe engineering toolset I'm building.
The workflow
Creating a chunk is no more difficult than creating a plan. We start by giving /chunk-create a rough direction of what we want to do. The agent uses a CLI to instantiate GOAL and PLAN templates and then folds your rough direction into the GOAL. The template guides the agent to investigate the broader context and ask you clarification questions regarding the desired result. When the command completes, you’ll have a GOAL file full of rich “why” and “why not” judgments that future agents will recognize and follow.
Then /chunk-plan instructs the agent to do a detailed implementation analysis given the code. This is where the agent conducts a deep exploration of the existing relevant code (and its back-referenced chunks) and builds exactly what the implementing agent needs to know to realize your vision while maintaining your previous judgments. The agent will fold its learnings into the PLAN template.
Now, your planning process was technically two steps, but required no additional judgment. You gained a distilled semantic understanding of the change that all future agents can use, and you gained a PLAN that incorporated your judgments for this work and those from earlier chunks.
Does this actually work? I analyzed 318 orchestrator transcripts to find out. (What’s an orchestrator? A future article will cover that.)
The data tells two stories. First, how often agents follow backreferences depends on what phase they’re in:
Phase
Followthrough Rate
Plan
62%
Complete
39%
Review
38%
Implement
23%

During planning, agents actively gather context, following most backreferences they encounter. By implementation, they’re heads-down coding. The 23% rate might look low, but it’s intentional: the PLAN already contains the context they need. Do your thinking in planning, do your coding in implementation.
Second, what agents read when they do follow:
Pattern
Frequency
GOAL.md only
53%
Both files
31%
PLAN.md only
16%

84% of the time, when the agent used a chunk reference, it read the GOAL (agents reach for the why first). The PLAN is there when they need implementation details, but most of the time, they don’t.
The two-file split isn’t overhead. It’s the natural structure agents already want.
Why this matters
One advantage of retaining the why is that you can refer back to it explicitly as you’re prompting the next chunk of work. “Hey, we’re debugging what we did in this chunk” — and you reference the chunk. You don’t need to explain the setup, how you got there, or what the scope was. All of that lives in the chunk.
This is a major unlock for picking up work left behind by a prior agent. Think about that bug in production that you didn’t see until long after the agent session that created it was lost. The medical record is there. The next surgeon can prime itself by reading it.
But chunks do more than solve amnesia. They hold the shape.
I think of chunk GOALs as tent-poles and stakes. They are points of judgment that help the sprawling codebase maintain its intended form. An agent working on a section of the tent can see the nearby poles and stakes without needing to understand the entire structure. They work locally, but are aligned.
Every chunk you write is like another page in your onboarding wiki that you never have to explain again. Future agents discover it through backreferences in the code — they trace from implementation to intent, exploring as needed. They’re not reading everything; they’re finding applicable context when they need it. The wiki page is there when the agent needs its insights.
Here's how this works in practice. An example from the vibe engineering codebase:

Without context, this looks like an arbitrary choice. Why :: instead of .? Why string prefix matching instead of AST comparison?
The GOAL.md explains that the :: separator was explicitly chosen so that overlap detection between chunks can be performed using simple string operations. If chunk A references foo.py#Bar and chunk B references foo.py#Bar::baz, containment is computable via startswith() — no parsing required.
The agent reading this code now understands the design force behind it. The choice isn't arbitrary; it's load-bearing.
The payoff
Your effort compounds into institutional memory. As the tent gets bigger, it gets more poles and stakes. The shape holds, and everyone feels a little safer running around inside.
I didn’t add documentation to my workflow. I just found a way to keep the documentation my prompting was creating around productively. Scoping the work was documenting it—no extra cost. The overhead I’d always resisted turned out to be work I was already doing — I wasn’t saving it.
We’ve solved surgeon amnesia with workflow, not effort. Conveniently, the next generation of meat-based junior developers we bring into the codebase will assimilate our judgment through the same artifacts.

Sidebar: How Agents Build Context
Agents are built on LLMs, and LLMs are stateless functions. All an LLM can use to generate its following response is the payload in the API request — there’s no persistent memory between sessions.
This payload typically includes:
System prompt — instructions from the agent developer (and things you provide via CLAUDE.md and skill definitions)
Conversation history — the back-and-forth so far, including tool call results
The latest user message — what you just asked
When you start a fresh session, the conversation history is empty. The agent has only the system prompt to work with. But what distinguishes an agent from old-school ChatGPT is that agents can build their own context as they explore. They grep around, read files, and accumulate understanding through tool calls. Each result is added to the conversation history, expanding what the agent knows.
This is all part of the emerging discipline of context engineering — designing what goes into that payload so agents arrive educated and stay focused.
The problem: if the agent’s exploration finds only code, it won’t understand the forces that formed it. You end up with a surgeon obsessed with the symptoms but ignorant of the medical history. The result is that the agent does what you asked but also hallucinates worthless features, ignores architectural patterns, and reinvents things that already exist. It’s operating brilliantly on what’s there, but without the intent that caused it to be there.
How chunks help: When agents explore, backreferences in the code point them to chunk GOALs. Instead of inferring intent from implementation, they can read it directly. The context they build includes why, not just what.


