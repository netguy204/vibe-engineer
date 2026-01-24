# Article Writing Workflow

## Article Metadata

| Field | Value |
|-------|-------|
| Article Number | 1 |
| Working Title | The Uncomfortable Truth About AI Coding |
| Target Audience | Engineering leaders helping organizations adopt agentic workflows, and senior developers skeptical of VibeCoding's tendency to produce slop |
| Core Thesis | Vibe coding fails because it's an onboarding problem we're ignoring. Every new agent session is a new junior to onboard—and we already know how to do that. |
| Source Material | articles.md outline, Bryan Cantrill's "Sharpening the Axe" talk |

---

## Current Phase

**Phase:** 4-Voice Check

**Status:** Full draft complete; all sections have voice capture and assembly

**Next Action:** Human reviews full draft for voice; resolve remaining uncertainties

---

## Restructured Outline

Based on your voice capture, here's the natural shape that emerged:

### 1-3. The Setup → Recognition → Reframe (tightened)
- Opening: Goal is to convince graybeard friends their skepticism may be misplaced
- The first vibe: Magic stays with us
- **Early recognition**: Those of us in management recognized what came next—it's undertrained juniors
- Junior vs agent initial state: Blank eyes and a burning desire to please
- Failure modes as *illustration*: 95% success, then context overflow or new-session amnesia
- Root cause: Lack of context and mismanaged attention
- Why juniors succeed: Episodic memory + discoverable patterns
- Why agents fail: Brand new idiot savant every morning + no patterns to discover
- **The insight**: This is an onboarding exercise we do multiple times a day
- What mature orgs learned: Team sport, outsource to documentation
- The requirement: Produce code AND artifacts to onboard the next generation

### 4. The Thesis (The puzzle and the payoff)
- The puzzle: How to onboard agents every time we open the terminal
- The metaphor: CLAUDE.md is what HR handed them on the way in
- The payoff: Day 2 can feel as magical as day 1
- The leverage: Clarifying documentation = every future agent understands your refined vision
- The value proposition: Your judgment (not your typing) is exactly what you're bringing to the vibes

### 5. The Nuance (Agents aren't just fast juniors)
- Superhuman working memory and synthesis
- Once onboarded properly: Incredible leverage for thinking at larger scales
- "What would it mean if we changed X?" → brilliant insight, better designs

### 6. The Primacy of Toolmaking [NEEDS VOICE CAPTURE]
- Cantrill's insight on toolmaking
- Documentation as toolmaking for agent development
- Why it feels like overhead (immediate cost, delayed payoff)

### 7. What's Coming [NEEDS VOICE CAPTURE]
- This series as field notes
- The journey ahead

---

## Current Draft (Sections 1-5)

**Note:** Sections 1-3 restructured to get to onboarding faster. Ready for your voice edit pass.

---

My goal here is to convince my graybeard engineer friends that their current impressions about the long-term viability of software development with AI may have been biased by improper usage.

We all remember the first time we vibed. It was probably something cliché—a snake game or a todo app—but the magic was real. You went from an idea to functional and pretty decent code in 1% of the usual time.

Most likely that first vibe was a 95% success scenario. You didn't really start to hit pain until you tried to tackle that remaining 5% blocking completion. The back-and-forth prompts eventually overwhelmed the model context window. You started a new session, and this new agent has no memory of all that you had tought the first one. It was still smart it became like a world-class surgeon who can't remember which leg you discussed. Brilliance without context is a specific kind of dangerous.

Those of us in management have seen this before—sort of. Juniors start safely incompetent; they learn context before they're dangerous. They have episodic memory. They get a few weeks to figure things out. They can remember the lesson you taught them last week. And the codebase they're working in probably wasn't built exclusively by other juniors, so there are discoverable patterns to learn from.

Agents don't get that grace period. They arrive ready to operate, with no idea which leg is which. Every session is a world-class surgeon with amnesia. And if the codebase was built by previous amnesiac surgeons, there are no higher intents to learn from the code.

We've identified the problem: Vibe Engineering (multi-day vibe coding) is an onboarding exercise. But, unlike the one we do once every couple months to bring on a junior, it's an onboarding exercise we do multiple times a day. Fortunately, we already know what works—a growth plan, documentation, guardrails, and process.

- Onboarding is progressive discovery: All you need to know right now is what's necessary to find or do the next thing. Being told more than that is overwhelming.
- Onboarding captures intent, not just mechanics: Knowing *how* to do something isn't enough. "We use PostgreSQL" is mechanics. "Because we need ACID transactions" is intent. "We learned this migrating off distributed Mongo when eventual consistency broke us" is wisdom. Juniors can ask for all three. Agents only get what you wrote down.
- Onboarding is a team sport: If only the team lead can onboard newcomers, then bringing in newcomers destroys the capacity of the team by saturating its leadership.
- Onboarding is eventually carried by documentation: The junior has more free time than anyone else on the team. If they can apply that time to self-directed learning then onboarding scales. Documentation also survives the onboarder. Good documentation is institutional memory that doesn't walk out the door.
- Onboarding has guardrails: Code review, PR templates, linters. The newcomer can't easily make catastrophic mistakes while they're still learning. The constraints protect the codebase *and* the newcomer.
- Onboarding is testable: You know it worked when the newcomer's output respects the patterns without hand-holding. If you're still correcting the same mistakes, then you've discovered an area for improving your onboarding.

Now, getting back to vibe coding. The reason it falls apart when applied to a legacy codebase or on day 2 of a greenfield vibe project is this problem of onboarding. If you're patient, you can give the day 2 agent a robust enough prompt to get the job done. But writing prompts that rich doesn't feel like magic anymore-it feels like documenting. And most of us didn't become engineers to write documentation.

So the puzzle is: how do we onboard agents every session without it feeling like a career change?

And here's the thing graybeards know but rarely say out loud: our value was never typing speed. It was knowing what to build and recognizing whether it was built right. The good news is that the value of judgment doesn't disappear when agents do the typing—it becomes the whole game.

---

If every new session is like a new junior to onboard then the CLAUDE.md file is what HR handed them on the way in. But HR doesn't hand the junior the entire company wiki on day one—they'd drown. Agents have the same problem with a different name: the context window. The answer isn't a bigger wiki or a longer CLAUDE.md. It's documentation that can be discovered from wherever you start—code that links to the intent behind it, explorable on demand. And here's the leverage: every clarification you make to that documentation means every future agent understands your refined vision. Judgment applied to docs compounds in a way judgment applied to code never did.

---

Toolmaking has always been one of the highest leverage activities an engineer can engage in. Bryan Cantrill makes this case beautifully in his P99 talk "Sharpening the Axe"—better tools yield better artifacts, even when the tools themselves are invisible in the final product.

This is what I'm building: tools that create a rich onboarding environment where agents and humans can both become productive in a codebase. Documentation that grows with the code. Intent that stays linked to implementation. The wiki we always wanted but could never afford to maintain—made sustainable because agents help write it as they work.

I'm doing this because I want my judgment to have more impact, not less. In this series, I'll take you through what I've learned—and what I'm still learning—as I design the tools my organization uses for what I'm calling "vibe engineering."

---

## Uncertainty Log

| Location | Uncertainty | Resolution |
|----------|-------------|------------|
| Section 3 para 4 | Changed "bluesky" to "greenfield" - verify this is what you meant | |

---

## What's Missing

**Beats I dropped because you covered them elsewhere or skipped:**
- Beat 2.3 "Unexpected breakage" - not captured, may not be needed
- Beat 4.2 "Investment required" - implied but not explicit
- Beat 5.3-5.5 (missing episodic memory, documentation as dual-purpose) - partially covered but could be expanded

---

## Revision History

| Date | Phase | Change |
|------|-------|--------|
| 2026-01-21 | 1-Decomposition | Initial outline created with 7 sections, 24 beats |
| 2026-01-23 | 1→2 | Restructured outline to match voice capture; "onboarding" becomes central metaphor |
| 2026-01-23 | 2→3 | Initial flow draft for sections 1-5 |
| 2026-01-24 | 3→4 | Restructured sections 1-3: moved junior recognition earlier, failure modes now illustrate the pattern |
| 2026-01-24 | 4 | Replaced "idiot savant" with surgeon/amnesia metaphor + "brilliance without context is dangerous" |
| 2026-01-24 | 4 | Expanded onboarding principles list (6 bullets after cutting "layered") |
| 2026-01-24 | 4 | Added closing section: toolmaking + series tease merged into one |
| 2026-01-24 | 4 | Folded superhuman synthesis into leverage section; cut standalone section |
