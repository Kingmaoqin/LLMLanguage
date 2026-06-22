"""Convenience wrapper for the smallest Stage-2.5 smoke."""

from __future__ import annotations

import sys

from scripts.run_stage2_5_experiment import main


if __name__ == "__main__":
    sys.argv.extend(["--phase", "smoke"])
    main()
