---
article_number: 1
title: "The Uncomfortable Truth About AI Coding"
status: DRAFTING
---

This series is an introduction to what I call "Vibe Engineering". I hope it convinces my graybeard engineer friends that their skepticism about AI coding may stem from improper use rather than the technology itself.



We all think of the first time we vibe-coded. It felt like magic. We went from an idea to functional and pretty decent code in 1% of the usual time.



Most likely, that first vibe was a 95% success scenario. You didn't really start to hit pain until you tried to tackle the remaining 5% blocking completion. The back-and-forth prompts eventually overwhelmed the model context window. You started a new session, and this new agent has no memory of what you taught the first one. It was still smart, but it became like a world-class surgeon who can't remember which leg you're talking about. Brilliance without context is especially dangerous.



Those of us in management have seen this before (sort of.) Juniors start out safely incompetent; they learn context before they become dangerous. They have episodic memory. They usually get at least a few weeks to figure things out. They can remember the lesson you taught them last week. And the codebase they're working in probably wasn't built exclusively by other juniors, so there are discoverable patterns to learn from.



Agents don't get that grace period. They arrive ready to operate, with no idea which leg is which. Every session is with a world-class surgeon with amnesia. And if the codebase was built by previous amnesiac surgeons, there is no higher intent to learn from the code.



We've identified the problem: Vibe Engineering (making vibe coding sustainable) is an onboarding exercise. But unlike the one we do once every couple of months to bring on a junior, it's an onboarding exercise we do multiple times a day.



Fortunately, we have already discovered what works. Good onboarding is progressive: just enough information to find the next thing, not a firehose. It captures intent, not just mechanics. It scales through documentation, so it doesn't saturate your senior people. And it has guardrails so newcomers can't easily make catastrophic mistakes while learning.



The reason vibe coding falls apart on day 2 of a greenfield project (or immediately on a legacy codebase) is that none of this infrastructure exists for the agent. You *can* give the day 2 agent a solid enough prompt to get the job done. But writing prompts that rich don't feel like magic anymore; they feel like writing documentation. And most of us didn't become engineers to write documentation.



So the puzzle is: how do we onboard agents every session without it seeming like a career change?



And here's the thing, graybeards know but rarely say out loud: our value was never typing speed. It was knowing what to build and recognizing whether it was built right. The value of judgment doesn't disappear when agents do the typing; it becomes the whole game.



If every new session is like a new junior to onboard, then the bootstrap context (CLAUDE.md in my setup) is what HR handed them on the way in. But HR doesn't require the junior to read the entire company wiki on day one; they'd drown. Agents have the same problem with a different name: the context window. The answer isn't a bigger reading assignment or a longer bootstrap context. It's documentation that can be discovered from wherever you start; code that links to the intent behind it, explorable as needed. And here's the leverage: every improvement you make to that documentation means every future agent understands your refined vision. Judgment applied to onboarding docs compounds in a way judgment applied to code never did.



Toolmaking has always been one of the highest leverage activities an engineer can engage in. Bryan Cantrill makes this case beautifully in his P99 talk "Sharpening the Axe": better tools yield better artifacts, even when the tools themselves are invisible in the final product.



This is what I'm building: tools that create a rich onboarding environment where agents and humans can both become productive in a codebase. Documentation that grows with the code. Intent that stays linked to implementation. All culminating in the wiki we always wanted but could never afford to maintain, made sustainable because agents help write it as they work.



I'm doing this because I want my judgment to have more impact. In this series, I'll take you through what I've learned (and what I'm still learning) as I design the tools my organization uses for Vibe Engineering.

  