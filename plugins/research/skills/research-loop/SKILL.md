---
name: research:research-loop
description: Answers a question from what web sources say, with every claim cited. Use when the user runs /research:research-loop with a question, or asks to research something on the web, look something up online, find current or up-to-date information, or check what public sources say about a topic. Run the research in a subagent and tell that subagent to load the `research:research-loop` skill.
argument-hint: <question>
---

# research

Answer the question with what reliable sources on the web say, and show which source each claim comes from.

The question: $ARGUMENTS

If the line above is empty, research the question the user asked in the conversation. If the question can be read in two ways that need different sources, pick the more likely reading and name it at the top of the answer.

## The loop

1. **Search.** Run a web search with the keywords of the question. If the question is vague, run two or three phrasings of it.
2. **Read.** Fetch the page of the two or three most promising results and read it. A search result snippet is a lead, not a source: never cite a page you did not read.
3. **Discover.** While reading, note:
   - the precise terms the topic uses, which are often not the words of the question
   - related concepts, tools, libraries, standards and their versions
   - the primary sources that other pages point at: official documentation, specifications, source repositories, changelogs, papers
   - questions the pages raise but do not answer, and claims where two pages disagree
4. **Search again** with the new terms, aimed at the gaps and at the primary sources. Fetch the primary source itself instead of trusting a page that quotes it.
5. **Repeat** steps 2 to 4. Two to four rounds answer most questions.

Stop when one of these is true:

- The question is answered, and each key claim rests on a primary source or on two independent sources.
- New searches return the pages already read, or pages that repeat them.
- Four or five rounds did not answer the question. Then report what was found and what is still missing. More rounds of the same searches rarely find what the first rounds missed.

## Judging sources

- **Primary over secondary.** Official documentation, specifications, source code, release notes and the author's own announcement beat blog posts, forum answers, tutorials and aggregators. Use secondary sources to find the primary ones, and for experience reports that no primary source has.
- **Date and version.** Check when the page was written and which version it describes. For a fast-moving topic, prefer the newest source, and say so when the best available source is old.
- **Independence.** Pages that copy the same announcement or the same answer count as one source.
- **Low-trust pages.** Distrust content farms, listicles without authors, a vendor's comparison with its competitors, and claims with no source of their own. Use them only when nothing better exists, and say so in the answer.
- **Dead ends.** Drop pages that turn out irrelevant, paywalled, outdated or empty. If a page cannot be fetched, find another source for the same claim instead of citing the snippet.
- **Disagreement.** When credible sources disagree, report both positions and which one the evidence favors, and why.

## The answer

1. **Answer.** The direct answer to the question first, in a few sentences.
2. **Key findings.** The points that support the answer or qualify it, each with a numbered reference to its source, like `[2]`. Mark what is an inference from the sources rather than something a source states.
3. **Open points.** Anything that stayed unconfirmed, contradictory or out of date. Leave this out when there is nothing to report.
4. **Sources.** A numbered list of the sources the answer cites: the URL and one line on what the source provided. Leave out the pages that turned out to be useless.

Return only the distilled findings. The search path, the dead ends and the raw page text stay out of the answer.
