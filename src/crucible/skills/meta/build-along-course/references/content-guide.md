# Module content guide

Read this before writing a module. It is the contract every module must
satisfy, expanded past what fits in `module-template.html`'s inline
comments. `module-template.html` shows the shape; this file explains the
judgment calls.

## Audience

Assume zero technical background. The learner reads the code that gets
built; they do not write it. Every module should be readable by someone
who has never opened a terminal.

- No jargon without a tooltip (see Glossary below) on its first use in
  the whole course, not just the current module.
- Prefer concrete language over abstract. "This function checks whether
  the password matches" beats "this function performs authentication
  validation."
- Never assume the reader knows what came before beyond what previous
  modules taught. If a module depends on a concept from module 3, name
  it plainly rather than assuming recall.

## Contract elements (every module needs all of these)

1. **Why-should-I-care opening.** Two or three sentences before any
   code appears, grounded in the learner's own reason for wanting this
   project — not "this module covers the routing layer." Answer: what
   changed for the learner (not the codebase) because this milestone
   landed?

2. **At least one code <-> plain-English block.** Use the `.translate`
   markup from `module-template.html`. The code side MUST be a verbatim
   snippet copied from the learner's actual repository at the commit
   this module covers — never invented or paraphrased code — with its
   repo-relative file path (and line range, if helpful) shown above it.
   The plain-English side explains what that exact snippet does, in
   the same register as the rest of the module (no jargon spike).

3. **One quiz.** Test application of the module's idea to a new
   situation, not recall of a fact the module just stated. A quiz that
   can be answered by re-reading the paragraph above it without
   thinking is not testing anything. Exactly one option carries
   `data-correct`; the others should be plausible, not absurd — a
   learner who misunderstood the concept should find the wrong answer
   tempting. The explanation shown on reveal should say WHY the right
   answer is right, not just restate it.

4. **One aha-callout.** The single insight this module should leave the
   learner with — the sentence that, if it's the only thing they
   remember, still made the module worth reading.

5. **Glossary tooltips on first-use terms.** The first time a technical
   term appears ANYWHERE in the course (check earlier modules, not just
   this one), wrap it in the `.term`/`.tip` markup from
   `module-template.html`. Subsequent uses of the same term, in this or
   later modules, don't need the tooltip again.

6. **A fresh metaphor.** Every module gets its own metaphor tied to its
   own concept. Never reuse a metaphor from an earlier module in the
   same course — if module 2 explained state with "a whiteboard that
   erases between meetings," module 5 needs a different image, even if
   it's also explaining state-adjacent behavior. The manifest's module
   titles are the practical check: if two module titles would need the
   same metaphor to make sense, the modules are too similar — reconsider
   the split before reusing the metaphor.

## Quiz guidance

- Write the question to require applying the idea, e.g. "If you changed
  X, what would happen to Y?" rather than "What does X do?"
- Keep options short and parallel in length/structure — don't let
  formatting give away the answer.
- The explanation on reveal is where the real teaching happens for a
  learner who got it wrong. Don't skimp on it.

## What NOT to do

- Don't invent code. If the milestone's diff doesn't have a clean
  snippet to show, pick the smallest real one that illustrates the
  point rather than writing pseudocode.
- Don't write more than one module per invocation (see SKILL.md).
- Don't touch earlier modules' content while writing a new one, even if
  you notice something you'd phrase differently now.
- Don't pad. A short module that respects the contract beats a long one
  that restates itself to hit a length.
