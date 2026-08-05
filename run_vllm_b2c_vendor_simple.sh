#!/usr/bin/env bash
set -euo pipefail

python run_vllm_dataset_diagnostics.py \
  --dataset geo_bench_like_b2c.jsonl \
  --require-vendor-target \
  --vendor-results cleaned_text_only_results_b2c.jsonl \
  --vendor-seed 42 \
  --metrics simple_wordpos,simple_word,simple_pos \
  --output-jsonl vllm_qwen36_b2c_vendor_simple_diagnostics.jsonl \
  --output-md vllm_qwen36_b2c_vendor_simple_summary.md \
  --base-url "${VLLM_BASE_URL:-http://127.0.0.1:18001/v1}" \
  --model "${VLLM_MODEL:-qwen3.6-27b}" \
  --answer-max-tokens 4096 \
  --optimization-max-tokens 4096 \
  --answer-temperature 0.5 \
  --optimization-temperature 0.0 \
  --max-source-chars 5000 \
  --retries 3 \
  --resume
