# Benchmark Version Freeze

Generated: 2026-06-16T23:25:03.644311+00:00

## Active tau2 Source

- tau root: `/home/xqin5/tau2-bench`
- tau package path: `/home/xqin5/tau2-bench/src/tau2/__init__.py`
- tau package version: `NO_VERSION`
- distribution version: `1.0.0`

## Git

- branch: `main`
- HEAD: `ddc66a777e520373975f15d3abec989cfe2ec371`
- describe: `voice-user-sim-v1.0-90-gddc66a7`
- origin/main: `ddc66a777e520373975f15d3abec989cfe2ec371`
- status short: `M src/tau2/data_model/message.py`

The current tau2 working tree is frozen as-is. No benchmark upgrade or cleanup was performed.

## Dirty Diff

```diff
diff --git a/src/tau2/data_model/message.py b/src/tau2/data_model/message.py
index 0449e2f..76691fc 100644
--- a/src/tau2/data_model/message.py
+++ b/src/tau2/data_model/message.py
@@ -1,4 +1,5 @@
 import json
+import ast
 from copy import deepcopy
 from typing import Literal, Optional
 
@@ -71,6 +72,17 @@ class ToolCall(BaseModel):
         description="The requestor of the tool call.",
     )
 
+    @field_validator("arguments", mode="before")
+    @classmethod
+    def parse_string_arguments(cls, value):
+        if not isinstance(value, str):
+            return value
+        try:
+            parsed = json.loads(value)
+        except json.JSONDecodeError:
+            parsed = ast.literal_eval(value)
+        return parsed
+
     def __str__(self) -> str:
         lines = [f"ToolCall (from {self.requestor})"]
         if self.id:
```

## Data And Code Snapshot

- snapshot directory: `/home/xqin5/llmlanguage/ir_mstu_stage2/artifacts/stage2_5b/benchmark_snapshot`
- SHA256 file: `/home/xqin5/llmlanguage/ir_mstu_stage2/artifacts/stage2_5b/benchmark_snapshot/SHA256SUMS`
- files copied: 67

Included categories: retail/airline task definitions, policies, DB fixtures, split files, task issue records, domain tools/environments/data models, evaluator implementation, tau2 task/message/simulation data models, environment core, registry/run/config files, and user-simulator guidelines.

## tau2 check-data

The required CLI check was attempted with `conda run -n agentsearch tau2 check-data` before freezing. It failed because the CLI entrypoint resolved through `/home/xqin5/.local/bin/tau2` and then lacked `tokenizers` in that import path. This is recorded as an environment issue; direct `conda run -n agentsearch python -c 'import tau2'` succeeds.
