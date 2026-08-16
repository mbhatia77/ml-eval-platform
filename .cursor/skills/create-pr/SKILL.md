---
name: create-pr
description: Create a GitHub pull request from the current branch using gh. Use when the user asks to create a PR, open a pull request, or draft a PR description.
---

# Create PR

## Hard rules

- Do not commit unless the user already asked to commit
- Do not force-push
- Do not skip hooks
- Use `gh` for all GitHub work
- Never include secrets, `.env`, or credentials

## Workflow

Run these in parallel first:

1. `git status`
2. `git diff` and `git diff --staged`
3. `git log` and `git diff main...HEAD`
4. Check whether the branch tracks a remote and is up to date

Then:

1. Create a branch if still on `main`
2. Push with `-u` if needed
3. Open the PR with `gh pr create`

## Title

Keep it short and specific. Prefer:

- `Add decision router tests`
- `Fix CI pytest path`
- `Document evaluation routing rules`

Avoid vague titles like `Updates` or `Fix stuff`.

## Body template

```markdown
## Summary
- What changed and why

## Test plan
- [ ] `pytest` passes locally
- [ ] CI is green
- [ ] No secrets or `.env` files included
```

Use this exact command shape:

```bash
git push -u origin HEAD

gh pr create --title "the pr title" --body "$(cat <<'EOF'
## Summary
- ...

## Test plan
- [ ] ...

EOF
)"
```

## Checks before opening

- Evaluation logic stays in `src/evaluation/`
- API routing is not mixed into evaluation modules
- Tests live in `tests/`
- Decision routing stays deterministic and does not call external services

## After create

Return the PR URL.
