# repar plugin — proposed changes from the goal-form redesign run (2026-08-26)

Target repo: `git.coreop.net/titansoft/ai/agent-marketplace`, files under `plugins/repar/skills/spec-driven-development/`.
Apply from the marketplace repo root: `git apply --check -p1 repar-proposal.patch && git apply -p1 repar-proposal.patch`. Generated against the local marketplace checkout on 2026-08-26 (equal to the installed repar 1.0.1 cache); dry-run applied cleanly on a copy. The patch is beside this file as `repar-proposal.patch`.

## Why — one run's evidence
1. **Tier re-check after the Intent gate.** The Small-Change Tier requires "no open decision"; grilling is what closes decisions, so the tier can only be judged *after* Phase 0. This run judged it before, and ran spec + mermaid journey + interrogation pass + breakdown gate for a 170-line, one-layer UI restyle (290 lines of documents). Both gates were answered "confirm" with no change.
2. **Review agents scaled to diff size.** Three Opus axes on a 170-line diff reported the same two MEDIUMs (redundant `net`/`debtsById` props, duplicated CSS rule) under two labels each — ~230k subagent tokens for findings one reviewer would have produced.
3. **UI loop checklist per branch.** Fix pass #1 was re-verified on two of three goal kinds; the third crashed on first render. Only the fix-pass verifier caught it. "Each changed view" needs "and every branch of it", as a checklist the fix pass re-runs.
4. **Evidence = stable facts.** Cache-buster numbers narrated in the Progress Log drifted four times and became a Spec-axis finding — the process generating work about itself.

Not proposed: removing the tri-axis review or the fix-pass verification. The verifier caught the only serious bug of the session, and the bounded two-round loop worked exactly as designed.

## Changes (4 hunks)
- `SKILL.md` Phase 0: step 4 — tier re-check after the alignment gate.
- `SKILL.md` Path B "UI feedback loop": per-view, per-branch checklist that fix passes re-run in full.
- `SKILL.md` Feature Folder Management: evidence records stable facts only.
- `references/review-policy.md`: one reviewer for diffs under ~200 lines in one layer; three parallel only across layers or above that size.
