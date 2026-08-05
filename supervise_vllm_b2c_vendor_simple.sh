#!/usr/bin/env bash
set -uo pipefail

output="vllm_qwen36_b2c_vendor_simple_diagnostics.jsonl"
log="vllm_qwen36_b2c_vendor_simple_run.log"

while true; do
  ./run_vllm_b2c_vendor_simple.sh 2>&1 | tee -a "$log"
  runner_status=${PIPESTATUS[0]}

  if python - "$output" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
with path.open(encoding="utf-8") as handle:
    rows = [json.loads(line) for line in handle if line.strip()]
lines = [row.get("line") for row in rows]
complete = (
    len(rows) == 160
    and len(set(lines)) == 160
    and all(row.get("status") in {"ok", "skipped"} for row in rows)
)
raise SystemExit(0 if complete else 1)
PY
  then
    echo "B2C experiment complete: 160 unique ok/skipped rows" | tee -a "$log"
    exit 0
  fi

  echo "Runner exited with status $runner_status before completion; resuming in 60s" | tee -a "$log"
  sleep 60
done
