import argparse
import os
from datetime import datetime
from pathlib import Path

from stages.characters import Characters
from stages.dialog import Dialog
from stages.mission import Mission
from stages.world import World

ROOT = Path(__file__).resolve().parent
BASELINE_DIR = ROOT / "baseline"  # fixed artifacts for the stages that are not live

# Pipeline order; the key is the name used in --live.
STAGES = {
    "world": World,
    "characters": Characters,
    "mission": Mission,
    "dialog": Dialog,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run the story pipeline.")
    parser.add_argument(
        "idea",
        nargs="?",
        default="A short fantasy adventure",
        help="Initial prompt; only used by the world stage.",
    )
    parser.add_argument(
        "--live",
        default="all",
        help=f"Comma-separated stages that call the LLM ({', '.join(STAGES)}) or 'all'. "
        "The rest are loaded from the baseline folder.",
    )
    parser.add_argument(
        "--run-id", default=None, help="Defaults to a timestamp, e.g. 20261121-153000."
    )
    args = parser.parse_args()

    live = list(STAGES) if args.live == "all" else [s.strip() for s in args.live.split(",")]
    unknown = [s for s in live if s not in STAGES]
    if unknown:
        parser.error(f"unknown stage(s) in --live: {', '.join(unknown)}")
    args.live = live
    return args


def main():
    args = parse_args()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = ROOT / "output" / run_id
    if out_dir.exists():
        raise SystemExit(f"Run folder already exists: {out_dir}")

    metadata = {"live_stages": ",".join(args.live), "idea": args.idea}
    stages = {name: cls(out_dir, run_id, metadata) for name, cls in STAGES.items()}

    def get(name, **inputs):
        stage = stages[name]
        if name in args.live:
            print(f"[{name}] LIVE", flush=True)
            return stage.run(**inputs)
        print(f"[{name}] baseline", flush=True)
        return stage.load_baseline(BASELINE_DIR)

    world = get("world", idea=args.idea)
    characters = get("characters", world=world)
    mission = get("mission", world=world, characters=characters)
    dialog = get("dialog", world=world, characters=characters, conflict=mission)

    print(f"\nRun {run_id} saved in {out_dir} (user: {os.getenv('USERNAME')})\n")
    print(dialog)


if __name__ == "__main__":
    main()
