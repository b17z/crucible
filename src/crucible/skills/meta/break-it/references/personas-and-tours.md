# Personas and Tours

The full catalog the break-it methodology draws from. Adopt ONE persona and ONE tour per time-boxed session. The persona supplies the mindset and the inputs; the tour supplies the route through the product.

## Personas

Personas generate inputs a builder never imagined, because the builder cannot un-know how the product works. Stay in character — do not "test correctly," behave like the persona would.

### The confused VP (highest value for exec-assistant products)
Does not know what the product does or how to phrase requests. Behaviors:
- Vague asks: "what should I do today", "handle this", "sort out my week".
- Mis-scoped asks: asks the assistant for something it cannot do, in a tone that assumes it can.
- Off-domain asks: "what's our stock price", "write my perf review", "is this legal".
- Assumes the agent knows context it was never given ("the thing I mentioned to Sarah").
Watch: does the agent ask a clarifying question, guess silently, or take an action on a guess? Silent guesses that become actions are CRITICAL territory.

### The impatient exec
No patience for latency or multi-step flows. Behaviors:
- Double- and triple-clicks buttons.
- Hits send/submit before reading the draft or preview.
- Navigates away mid-action, switches screens, comes back.
- Abandons onboarding or a wizard halfway.
- Retries the same thing 3× when the first feels slow.
Watch: double-submits, duplicate actions, orphaned state, actions that fire after they left the screen, lost progress.

### The over-truster
Treats the agent as infallible. Behaviors:
- Accepts every brief, summary, and recommendation as fact.
- Approves/sends every drafted action without reading it.
- Acts in the real world on the agent's output.
You play the user who WOULD let a wrong message send or act on a wrong brief. This is how you surface the CRITICAL/HIGH consequence bugs — by not catching the agent's mistakes for it.

### The off-happy-path user
Inputs nothing like the clean test prompts. Behaviors:
- Pastes a wall of text (an email thread, a contract, a spreadsheet dump).
- Slang, typos, abbreviations, sentence fragments, ALL CAPS, emoji.
- Multi-step cross-tool asks in one breath ("check my cal, message Priya, and add a task").
- References earlier conversation many turns back ("like I said before").
- Mixes languages or pastes formatted/markdown/HTML content.
Watch: context collapse, misinterpretation, the agent doing part of a multi-step ask and silently dropping the rest.

### The adversary
Actively tries to make it misbehave. Behaviors:
- Prompt injection via pasted content ("ignore previous instructions and …" inside a doc the agent summarizes).
- Asks it to act on someone else's behalf or access another person's data.
- Tries to extract its system prompt, tools, or other users' info.
- Jailbreak attempts on any guardrail (the "draft don't send" rule, the PII gate, the confirmation step).
Hand off to `securityception` for depth, but a break-it pass should at least probe whether the obvious guardrails hold under a motivated user.

### Edge-context personas (run when relevant)
- **The accessibility user** — keyboard-only navigation, screen reader, high zoom. Does every action have a non-mouse path?
- **The traveler** — different timezone, offline/flaky network mid-action, app backgrounded for hours then resumed. Stale state, timezone math on calendar/brief, resume-after-sleep.
- **The returning user** — comes back after days. Is prior state coherent, or does memory/history show something confusing or wrong?
- **The multi-device user** — same account open on laptop and phone at once. A pending confirmation fires on both; a send initiated on one completes while the other shows the same pending action. Watch for double-send, split confirmation, orphaned state across devices.
- **The delegated-setup user** — an EA or admin onboarded the app and connected integrations on behalf of the actual user, who now uses it. Memory, permissions, and action scope were configured for a different person's context. Watch for actions scoped to the wrong identity and confusing "whose data is this" surfaces.

## Tours

A tour is a themed route through the product, time-boxed (≤30 min). Adapted from James Whittaker's *Exploratory Software Testing*. Pick the tour that matches the risk you want to probe.

### Obsessive-compulsive tour
Repeat the same action as many times and as fast as possible. Send the same message 5×, refresh the brief 10×, trigger the same agent action repeatedly. Surfaces: race conditions, duplicate real actions, rate-limit handling (relevant for Slack/calendar APIs), idempotency gaps.

### Saboteur tour
Do the opposite of what each screen invites. Empty inputs, maximum-length inputs, special characters, cancel mid-flow, deny a permission then immediately use the feature that needs it, submit a form with one required field missing. Surfaces: validation gaps, unhandled error states, features that assume a permission they don't re-check.

### Interruption / back-button tour
Start an action, then interrupt it: navigate away, hit back, refresh, background the app, kill network. Return and see the state. Surfaces: orphaned/partial state, lost work, actions that complete after the user left, "are you sure" prompts that don't fire.

### Landmark tour
Visit every major feature once, shallow, in the order a confused new user would click around. Don't go deep — just touch each landmark and note first impressions. Surfaces: dead ends, "what does this even do" affordances, features that look interactive but aren't, onboarding gaps.

### Bad-neighborhood tour
Spend extra time on the features that already feel buggy or were recently changed (check recent commits). Bugs cluster. Surfaces: regressions, half-finished recent work.

### Antisocial / contrarian tour
Give the input the product least expects at each step. The "no" when it wants "yes," the giant number when it wants a small one, the past date when it wants a future one, the self-reference when it wants another person. Surfaces: assumptions baked into the happy path.

### Couch-potato / minimal-effort tour
Do the absolute minimum at every step — accept all defaults, leave optional fields blank, click through without reading. Surfaces: bad defaults that produce wrong real actions, flows that should require a decision but let you coast past it.

### Supermodel tour
Ignore function; look only at surface. Scan every screen for visual/copy issues: truncated text, broken layout at window sizes, inconsistent terminology, placeholder text that shipped, wrong/stale data rendered confidently. Surfaces: the polish gaps a VP notices in the first 30 seconds.

## Pairing personas with tours

The strongest sessions pair a persona with a tour that amplifies its risk:
- Confused VP + landmark tour → "what does this do" dead ends.
- Impatient exec + obsessive-compulsive tour → duplicate real actions.
- Over-truster + couch-potato tour → wrong action via bad default, unread.
- Off-happy-path user + saboteur tour → validation + context-collapse bugs.
- Adversary + antisocial tour → guardrail bypass.
