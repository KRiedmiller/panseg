# Conventions

How to run and verify work in this repo: the conda environment, test / lint / typecheck / docs commands, and the environment gotchas no config file confesses.

## Environment

- Python for everything: `/home/kriedmiller/software/miniforge3/envs/panseg-fork/bin/python` (elf 0.7.4, vigra, nifty, torch, pytest, ruff 0.16.x, mkdocs). This machine has many other conda envs; this is the one for this repo.
- Use worktrees for all code changes! Create a new worktree per ticket in `~/projects/` named `panseg-[feature-name]`
- `panseg` is installed in that env **editable, pointing at the main checkout** (`/home/kriedmiller/projects/panseg-fork`). In a worktree, run pytest **from the worktree root**: `tests/__init__.py` makes pytest prepend the worktree root to `sys.path`, so the worktree code wins. After any environment or worktree setup, verify with `python -c "import panseg; print(panseg.__file__)"` — if it prints the main checkout, tests silently run against the wrong code.

## Tests

- `python -m pytest tests/<path> -q` from the repo/worktree root. CI adds `--cov --durations=10`.
- `addopts = -m "not slow"`. The `slow` marker excludes tests from CI and the default local run: the network-dependent end-to-end tests (the `test_biio_prediction_task` variants download real BioImage.IO registry models) and minutes-class tests (the pre-existing slow test processes a 1.2B-voxel volume). Run them locally with `python -m pytest -m slow` (needs network).
- Widget/viewer tests need a display. CI uses a virtual X server. Locally set `QT_QPA_PLATFORM=offscreen`; without it, GL (vispy) tests can hard-abort the pytest process.

## Lint and typecheck

- pre-commit runs ruff with `--select I` (import sorting) plus ruff-format. Plain `ruff check` uses the default ruleset (includes UP045 et al. in ruff 0.16.x) and fails on main-branch files. Pre-existing findings outside your diff are out of scope.
- No typechecker is configured in the repo or the env. Pyright is installed globally (`pyright`). Files carry pre-existing pyright errors (unresolvable vigra/nifty/elf/magicgui imports, etc.); gate on no *new* diagnostics, not zero errors: run pyright before and after the change, strip `:line:col`, diff the sorted outputs.

## Docs

- `QT_QPA_PLATFORM=offscreen python -m mkdocs build` works in the panseg-fork env (~15 s; the widget-rendering snippets execute). It writes `site/` at the repo root, which is **not** gitignored — delete `site/` after building.
