# Changelog

## 0.7.0

- Change the look of the HTML output from explain, retention-write, and tech-write so it no longer reads as AI-generated at a glance. The cream background and terracotta accent are gone. Each skill now uses one fixed pair of typefaces and accent color: explain uses Noto Sans JP with blue, retention-write uses Noto Serif JP with indigo, and tech-write uses IBM Plex Sans JP and IBM Plex Mono with green. Japanese typesetting rules are shared by all three: body lines are limited to 40em, strict line breaking and spacing between Japanese and Latin text apply to the body, and proportional spacing, balanced wrapping, and phrase-based line breaks apply to headings only. Table cells no longer break words, and figures and explain panels can extend to 52rem.
- In HTML, sources are now shown as superscript numbers linked to the source list. Markdown drafts keep the "(出典 n)" form. tech-review turns the superscript numbers back into "(出典 n)" when it extracts the text of an HTML document.
- The visual checklist for HTML now checks for common signs of AI-generated pages, such as small labels above headings, fade-in sections, emoji headings, and rounded shadowed cards on every block. retention-write sets only its one-sentence conclusion larger than the body text, and tech-write shows a fixed table of contents on the left only when a document has four or more h2 headings and the screen is at least 1100px wide.

## 0.6.0

- Add a topic overview document type to tech-write and tech-review, for documents that explain the concepts and mechanics of a technical topic such as Git Flow or OAuth. tech-write picks it up only when a document is requested (summarize it, write an explanation, make it a document), not for a plain "explain" question. It looks up the facts itself, gives each fact a source URL and the date it was checked, confirms definitions and specifications against primary sources (official documentation, specifications, or the original work) as explain does, marks facts it cannot source as needing confirmation, and states in the text when the facts date from (for example, the original publication date and any later notes by the author). It adds no evaluation or adoption recommendation of its own, and attributes any evaluation found in a source to whoever made it. A document for deciding whether to adopt the topic (a proposal) still goes to retention-write; summaries of a given paper or article, comparisons, drawn explanations, and tutorials are handled as before. tech-review audits such overviews with the same checklist.

## 0.5.0

- Add a research report document type to tech-write and tech-review, for comparisons of several options and for verification or measurement reports. tech-write does the research itself (web search, reading files and code, running commands, and throwaway measurement scripts in a temporary directory, leaving the user's repository unchanged). It sets the scope before writing and states it at the top, gives each fact how it was checked (URL, file and line, or command and output), lists what could not be verified both in a "could not verify" section and in the delivery report while marking the affected places as needing confirmation, and puts recommendations in a final section that points to the results they rest on. A document whose main purpose is the recommendation (a proposal) still goes to retention-write. English reports follow the same rules; the Japanese style checks and scan.py apply to Japanese drafts only. tech-review audits such reports with the same checklist. The rule on separating facts from interpretation in investigation comments now lives in the research report reference, and the comment reference points to it.

## 0.4.0

- Add a destination to tech-write and tech-review besides the document type: GitHub Markdown by default, or a short X post, an X Article, or a Slack message when one is named. Each destination's limits and syntax live in its own reference, read by both skills. For X, tech-write asks every time whether to fit one post, split into a thread, or write a long post (X Premium, not X Articles), and checks the weighted length with a new standard-library script before delivery; tech-review flags a post over the limit as high with the excess. Slack messages are delivered as mrkdwn text ready to paste. For X Articles, the plan, supported formatting and limits that cannot be confirmed from official help are marked as needing confirmation, and how pasted Markdown or HTML renders is still waiting for a hands-on check. Every destination gets the same pre-delivery checks as before, and post bodies are not turned into HTML.
- Add a source summary document type to tech-write and tech-review for papers and articles summarized without the writer's opinion. tech-write reads the whole source (every PDF page) before writing, checks numbers, conditions, and limitations against it, quotes minimally with the title and URL, and does not reproduce figures or tables. tech-review audits such summaries against the source with the same checklist. A blog post that introduces an article or paper is written as a source summary unless the request asks for the writer's opinion or impressions; such requests still go to retention-write.
- tech-review now also takes requests to polish or partly improve an existing reference document (README, procedure, Issue, and so on); a request that asks only for a rewrite still goes to tech-write. It still does not edit the document; it returns findings and suggested rewrites. When a review or polish request also asks for the fix ("fix it"), or the fix is asked for after the report, it reports first and then hands over to tech-write. A request that asks for both a review or polish and the fix ("review this procedure and rewrite it") now starts in tech-review even when tech-write picks it up first, so it always gets the report before the rewrite.
- tech-write now takes requests to rewrite part of a reference document (a section of a README, a chapter of a procedure), not only full rewrites. retention-write likewise takes requests to rewrite part of a document that argues for a decision (a section of an ADR or a proposal). Both keep the text outside that part unchanged and report issues found there separately.

## 0.3.0

- Run the tech-write readability pass on explain pages before delivery to reduce AI-sounding prose.
- Omit the empty "where the analogy breaks" section from explain pages that use no analogy.

## 0.2.0

- Treat PR descriptions as a document type and keep paragraphs focused on one point while preserving information.
- Flag long Japanese prose paragraphs as weak signals for contextual review.
- Include paragraphs revisited during a first read in reader checks.
- Plan the structure of multi-point technical documents before drafting, without adding unnecessary planning to short documents.
- Prevent retention-review from declaring a guarantee invalid based on an unverified relationship.

## 0.1.0

- Bundle five Japanese skills: retention-write, retention-review, tech-write, tech-review, and explain.
- Include shared writing principles and references, plus a Python scanner for Japanese prose.
- Provide English and Japanese installation instructions.
- Support local HTML explanations with claim-level verification status and stated limits of analogies.
