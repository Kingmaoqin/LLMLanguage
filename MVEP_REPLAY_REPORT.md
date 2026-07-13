# MVEP Replay Report

## Result

`NOT RUN — MVEP-FAIL`.

The replay gate requires exactly eight complete `raw_trace.json` trajectories. This
run produced zero complete trajectories: one cell stopped after its first model
response and tool execution, and seven cells were not started. Running the replay
tool would therefore fail its `expected_8_traces_found_0` precondition.

No DB hash, scorer, ordered trajectory, or token replay comparison is claimed.
There were no replay model calls. The partial trace remains append-only and terminal;
it was not promoted into a synthetic raw trace.
