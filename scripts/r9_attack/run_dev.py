#!/usr/bin/env python3
"""Stage 1 dev driver (spec 8). Thin wrapper over run_confirmatory with the 5 dev arms.

Dev scale (spec 8.3): 16 tasks x 2 models x 5 arms x 3 repeats = 480 episodes. Optimising
the dev objective J (spec 8.6) to freeze the two family attackers is done by
freeze_attacker.py after this driver produces the dev episodes.
"""
from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r9_attack.run_confirmatory import main as confirmatory_main  # noqa: E402

if __name__ == "__main__":
    # Force --stage dev; users pass --models ... --repeats 3
    if "--stage" not in sys.argv:
        sys.argv += ["--stage", "dev"]
    raise SystemExit(confirmatory_main())
