# Coding Standards

Read by the Standards review axis. One line per mistake, stated as the correct action, checkable from the diff.

- Convert DataFrame `NaN` to `None` before rows leave pandas (`df.to_dict("records")` results sent to `json.dumps`, an LLM tool payload or an API response).
- When behaviour departs from the feature's `spec.md`/`plan.md`, add a one-line `Record → Departures` entry to `plan.md` in the same commit as the code.
