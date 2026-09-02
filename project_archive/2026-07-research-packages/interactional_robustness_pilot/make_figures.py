from __future__ import annotations

import argparse
from pathlib import Path

from src.plotting import make_all_figures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results_dir", default="results/")
    parser.add_argument("--figures_dir", default="figures/")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    results_dir = Path(args.results_dir)
    figures_dir = Path(args.figures_dir)
    if not results_dir.is_absolute():
        results_dir = root / results_dir
    if not figures_dir.is_absolute():
        figures_dir = root / figures_dir
    make_all_figures(results_dir, figures_dir)


if __name__ == "__main__":
    main()

