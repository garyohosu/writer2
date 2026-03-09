from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from daily_short_story import RunDaily


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the daily short story pipeline scaffold.")
    parser.add_argument("--run-date", default=None, help="Override the pipeline run date (YYYY-MM-DD).")
    parser.add_argument(
        "--state-path",
        default=str(ROOT / "data" / "state.json"),
        help="Path to the state.json file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = RunDaily(run_date=args.run_date, state_path=args.state_path)
    state = runner.run()
    print(
        json.dumps(
            {
                "run_date": state.run_date,
                "stage": state.stage.value,
                "result": state.result.value,
                "current_slug": state.current_slug,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
