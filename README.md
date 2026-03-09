# writer2

`writer2` is a Python scaffold for the DailyShortStorySite pipeline described in [SPEC.md](SPEC.md). The current implementation focuses on:

- class-diagram contract coverage
- core domain models and persistence helpers
- publish/index primitives
- a minimal `run_daily.py` entrypoint

## Layout

- `daily_short_story/`: domain classes and pipeline scaffolding
- `scripts/run_daily.py`: CLI entrypoint
- `tests/`: contract tests and core behavior tests
- `SPEC.md`, `class.md`, `sequence.md`, `usecase.md`: design documents

## Run Tests

```powershell
py -3 -m pytest -q
```

## Run Locally

```powershell
py -3 scripts\run_daily.py --state-path data\state.json
```

This currently initializes or resumes `data/state.json` and advances the scaffolded pipeline state.

## OpenClaw Startup

OpenClaw should invoke the WSL-side Python entrypoint from the project root. With this repository located at `C:\PROJECT\writer2`, the corresponding WSL path is `/mnt/c/PROJECT/writer2`.

Example OpenClaw command:

```bash
wsl bash -lc 'cd /mnt/c/PROJECT/writer2 && if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi && mkdir -p logs && python3 scripts/run_daily.py --state-path data/state.json >> logs/cron.log 2>&1'
```

Recommended runtime assumptions:

- run from `/mnt/c/PROJECT/writer2`
- activate `.venv` when present
- redirect stdout/stderr to `logs/cron.log`
- keep `data/state.json` under versioned project data

## Notes

- The current codebase is intentionally small and test-driven from the class diagram plus core behavior tests.
- AI execution, review heuristics, and publishing are implemented as safe scaffolding, not as a production content pipeline yet.
