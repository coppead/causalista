## What this changes

<!-- One piece of the project per pull request. Say what changes and why, in a few lines. -->

## Checks

- [ ] `uv run pytest` passes
- [ ] `uv run pytest -m slow` passes, if anything under `src/causalista/verifier/` changed
- [ ] Training targets still come from the verifier, and nothing from `cases/simulados/` or `teste-v3` enters training
- [ ] Pages, if touched, are generated from records, not drawn by hand
- [ ] CHANGELOG.md updated under "Unreleased", if the change is visible to users
