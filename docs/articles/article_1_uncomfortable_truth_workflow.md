# Article Writing Workflow

## Article Metadata

| Field | Value |
|-------|-------|
| Article Number | 1 |
| Working Title | The Uncomfortable Truth About AI Coding |
| Target Audience | Engineering leaders helping organizations adopt agentic workflows, and senior developers skeptical of VibeCoding's tendency to produce slop |
| Core Thesis | AI agents are very fast junior engineers. We already know how to manage junior engineers - through documentation, constraints, and review. VIBE engineering is that playbook, adapted. |
| Source Material | articles.md outline, Bryan Cantrill's "Sharpening the Axe" talk |

---

## Current Phase

**Phase:** 1-Decomposition

**Status:** In Progress

**Next Action:** Agent creates granular outline, human reviews and approves

---

## Phase 1: Decomposition

**Owner:** Agent
**Goal:** Break the article into granular beats—specific points each section must hit.

### Outline

## 1. The Seduction

> My goal in this article is to convince my graybeard engineer friends that your current impressions about the long-term viability of software development with AI may have been biased by improper usage or improper tools. 

### Beat 1.1: The intoxicating first experience
The moment you first prompt and code appears. The feeling of power and speed.
> We all remember the first time we vibed. It was probably something cliché like a snake game or flappy bird or a todo app, but the magic stayed with us.

### Beat 1.2: The "it mostly works" trap
Code that runs but you don't fully understand. Ship it anyway because momentum feels good.
> If the result of this first attempt to build something was a total failure, it's likely either you were either way too ambitious or chose the wrong tools. But most likely your outcome was a 95% success scenario, and you didn't really start to hit pain until it was time to try to find that remaining 5% that was blocking completion.
> If you were vibing something fundamentally interactive, then the remaining 5% probably took the form of back-and-forth prompts to fix the interactions and tweak the flow. These were successful the first few times, but eventually overwhelmed the model context window. And the sensation was: "wow, my brilliant collaborator feels really stupid now."
> If your build was something more data oriented or back-end, this probably took the form of going off and testing the artifact, discovering some deficiency, and then realizing you needed to create a new agent session to fix the deficiency. Of course, this new agent is a brand new idiot savant with no memory of all that beautiful insight you rained upon the first agent... and so it did ridiculous things.

### Beat 1.3: The productivity illusion
Metrics look great. Lines of code. Features shipped. Everything seems fine.
> Both of these failure modes come down to lack of context and mismanaged attention. And they always happen. Maybe you started in a legacy project and the model made your changes but utterly disrespecting the patterns existing tools in your project. Here the agent didn't know what was important so it guessed from what it happened to find.

## 2. The Hangover

### Beat 2.1: Recognition of a familiar pattern
This isn't new. You've seen this code before—from undertrained juniors.
> Those of us who have done time in management probably recognize the pattern because we'd seen it in junior engineers that we were bringing into the team, and it was our job to fix it. These are all symptoms of lack of appropriate context.
> Eventually, as the junior matures, they will learn how to find the information they need to be successful, and they'll have a refining view of what success looks like, so they'll know when they need to look for information. But the initial state of a junior is a lot like the initial state of the Ai agent: blank eyes and a burning desire to please.

### Beat 2.2: The 3-month codebase problem
No one understands the codebase anymore. Onboarding is painful. Context is lost.
> The junior stands a chance at success at onboarding because, as a human, they have episodic memory. They can remember the lesson that you taught them last week. And the code base that they're working in probably wasn't also exclusively built by other juniors. So there are discoverable patterns and opinions there that they can learn from and embrace.
> The agent doesn't have these advantages. Generally it's a brand new idiot savant every morning. And if the codebase it's working in was built by previous idiot savants, then there's probably no patterns to grow from and discover. 

### Beat 2.3: Unexpected breakage
Changes break things in ways no one predicted. The system has become fragile.

### Beat 2.4: The speed paradox
You went faster, but now you're slower. Technical debt accumulated at AI speed.
> So this would appear to mean that all agentic roads lead to a world where the guiding patterns of the codebase are lost, buried in muck, and there is no path for anyone, agent or junior, to onboard to a codebase successfully. 

## 3. The Reframe

### Beat 3.1: We already solved this problem
Every mature organization developed practices for this exact situation—just with humans.
> But having said it that way, I think we've just identified the real problem. This is an onboarding exercise. Unlike the one that we do once every couple months or years to bring on a junior, it's an onboarding exercise that we do multiple times a day.


### Beat 3.2: The purpose of documentation practices
Not to slow people down, but to let them go fast safely. Guardrails, not barriers.
> The organizations that do a lot of onboarding have learned the things that new engineers need on day one to be successful rapidly. For example, they make onboarding a team sport because if only the team lead or the tech lead can onboard newcomers, then bringing in newcomers destroys the capacity of the team. 

> Also, as they mature their onboarding, they outsource more and more of the onboarding to documentation. They learn the places in the codebase that juniors need to explore first, guide them there, and they learn what big concepts exist in the codebase that need to be explained elsewhere. 

### Beat 3.3: Code review, architectural guardrails, documentation
The specific mechanisms that work. What they actually accomplish.

### Beat 3.4: The pattern recognition
AI agents need the same constraints that inexperienced contributors need.

## 4. The Thesis

> So the puzzle for us graybeard engineers who would like the acceleration of agents over the long period is discovering ways to onboard our agents every time we open the terminal.

### Beat 4.1: The core reframe—fast junior engineer
Treat AI as a very fast junior engineer. Not a replacement, not magic—a resource to manage.

### Beat 4.2: Investment required
Constraints, documentation, workflow investment. The implementation becomes mechanical once constraints are clear.

### Beat 4.3: Leverage, not replacement
The goal is amplification of human capability, not elimination of human judgment.

## 5. The Nuance: Superhuman Context, Missing Memory

### Beat 5.1: The "fast junior" framing is incomplete
Useful but not the whole story. Agents are profoundly different in two key ways.

### Beat 5.2: Superhuman context windows
An agent can read 41 chunks, 3 narratives, 2 investigations and synthesize coherently in seconds. No human holds that much in working memory.

### Beat 5.3: Missing episodic memory
Unlike juniors who accumulate institutional knowledge, agents start fresh each session. No recollection of yesterday's decisions.

### Beat 5.4: Documentation serves two purposes
Guardrails (constrain like a junior) AND Fuel (feed superhuman synthesis capability).

### Beat 5.5: Documentation as external memory
Compensating for what agents lack while amplifying what they excel at.

## 6. The Primacy of Toolmaking

### Beat 6.1: Cantrill's insight
Better tools yield better artifacts. Tools are invisible to the user and often not present in the end product.

### Beat 6.2: Documentation artifacts as tools
Chunks, narratives, subsystems, investigations—these are toolmaking for agent-driven development.

### Beat 6.3: The "stealing time" feeling
Toolmaking has immediate cost but delayed payoff. Explains why documentation feels like overhead.

### Beat 6.4: The payoff moment
When you see an agent traverse your entire project history and synthesize insights no human could hold in working memory.

### Beat 6.5: The CLI embodiment
The `ve` CLI is toolmaking that makes documentation-driven development sustainable.

## 7. What's Coming

### Beat 7.1: This series as field notes
Honest about struggles, showing evolution of discoveries over time.

### Beat 7.2: The journey ahead
What the remaining articles will explore. The practical discoveries.

### Phase 1 Completion Criteria
- [ ] Every section from the article plan is represented
- [ ] Beats are specific enough to prompt focused voice capture
- [ ] Human has reviewed and approved the outline structure

### Phase 1 Notes

Decomposed the 5-section outline from articles.md into 7 sections (split "The Nuance" and "Primacy of Toolmaking" from the Key Points into their own sections since they're substantial). Each section has 2-5 beats representing specific points to hit.

The beats are designed to be specific enough that you can write 1-3 sentences of raw thoughts against each one without needing to figure out "what am I supposed to say here?"

---

## Phase 2: Voice Capture

**Owner:** Human
**Goal:** Annotate each beat with freeform thoughts in your authentic voice.

### Instructions for Human

For each beat in the outline above, write your raw thoughts:
- Stream of consciousness is fine
- Don't worry about polish or transitions
- Capture the *feeling* and *insight*, not just the information
- If a beat doesn't resonate, note that—we can restructure

### Voice Capture Content

<!--
Human: Copy each beat header and write your thoughts beneath it.
Keep your annotations clearly separated from the outline.

Format:
### Beat 1.1: The intoxicating first experience
**Voice notes:** [your freeform thoughts here]
-->

(voice capture goes here)

### Phase 2 Completion Criteria
- [ ] Every beat has voice notes (or explicit "skip/restructure" note)
- [ ] Human feels the raw material captures their perspective
- [ ] Any structural concerns have been flagged

### Phase 2 Notes

(human notes on what felt natural vs forced, structural concerns)

---

## Phase 3: Assembly

**Owner:** Agent
**Goal:** Stitch voice notes into coherent paragraphs without adding ideas.

### Assembly Guidelines

The agent will:
1. Organize voice notes into flowing paragraphs
2. Add transitions between ideas
3. Smooth rough edges in phrasing
4. Flag uncertainties with `[UNCERTAIN: reason]` markers
5. NOT add new ideas, arguments, or examples
6. NOT remove ideas even if they seem tangential

### Assembled Draft

<!--
Agent: Write the assembled draft here. Use [UNCERTAIN: ...] markers
where you've inferred connections or where notes were ambiguous.
-->

(assembled draft goes here)

### Uncertainty Log

| Location | Uncertainty | Resolution |
|----------|-------------|------------|

### Phase 3 Completion Criteria
- [ ] All voice notes have been incorporated
- [ ] Uncertainties are flagged, not papered over
- [ ] Draft flows as a coherent piece
- [ ] No new ideas have been introduced

### Phase 3 Notes

(agent notes on assembly decisions, inferences made)

---

## Phase 4: Voice Check

**Owner:** Human
**Goal:** Revise anything that doesn't sound like you.

### Instructions for Human

Read the assembled draft and:
1. Mark passages that don't sound like your voice
2. Rewrite those passages in your words
3. Resolve any `[UNCERTAIN]` markers
4. Note patterns for future workflow improvement

### Voice Check Edits

<!--
Human: Either edit the assembled draft directly (above) or note edits here.
If editing directly, use ~~strikethrough~~ for removed text and **bold** for additions.
-->

(edits and revisions go here)

### Phase 4 Completion Criteria
- [ ] Human has read the full draft
- [ ] All `[UNCERTAIN]` markers are resolved
- [ ] Human confirms the draft sounds like them
- [ ] Patterns noted for workflow improvement (if any)

### Phase 4 Notes

(human notes on voice drift patterns, workflow improvements needed)

---

## Phase 5: Polish

**Owner:** Agent
**Goal:** Final pass for clarity, grammar, and flow.

### Polish Guidelines

The agent will:
1. Fix grammar and punctuation
2. Improve sentence clarity where possible
3. Smooth any remaining rough transitions
4. Check for consistency in terminology
5. NOT change voice or tone
6. Flag any remaining concerns for human decision

### Polished Draft

<!--
Agent: Write the final polished version here.
This becomes the publication-ready draft pending human approval.
-->

(polished draft goes here)

### Polish Log

| Change | Rationale |
|--------|-----------|

### Phase 5 Completion Criteria
- [ ] Grammar and punctuation are correct
- [ ] Transitions flow smoothly
- [ ] No voice/tone changes introduced
- [ ] Human has approved final draft

### Phase 5 Notes

(agent notes on polish decisions)

---

## Workflow Retrospective

**Complete this after the article is finished.**

### What Worked Well

(note aspects of the workflow that felt smooth)

### What Felt Friction

(note aspects that were awkward or slow)

### Proposed Workflow Changes

(specific changes to the template for future articles)

---

## Revision History

| Date | Phase | Change |
|------|-------|--------|
| 2026-01-21 | 1-Decomposition | Initial outline created with 7 sections, 24 beats |
