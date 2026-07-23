#!/usr/bin/env python3
"""Inspect and summarize the committed vLLM GEO experiment results."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
for path in (ROOT_DIR, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_vllm_onequery_full_diagnostics as oneq  # noqa: E402


DEFAULT_RESULTS = "vllm_qwen36_b2b_vendor_simple_diagnostics.jsonl"
DEFAULT_DATASET = "geo_bench_like_b2b.jsonl"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=DEFAULT_RESULTS)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--line", type=int, help="Inspect one original dataset line.")
    parser.add_argument("--method", default="baseline")
    parser.add_argument("--show-answer", action="store_true")
    parser.add_argument("--show-prompt", action="store_true")
    parser.add_argument("--max-source-chars", type=int, default=5000)
    return parser.parse_args()


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def find_line(rows, line_no):
    for row in rows:
        if row.get("line") == line_no:
            return row
    raise ValueError(f"Line {line_no} not found")


def method_block(row, method):
    if method == "baseline":
        return row["baseline"]
    for block in row.get("methods", []):
        if block.get("method") == method:
            return block
    raise ValueError(f"Method {method!r} not found on line {row.get('line')}")


def print_summary(rows):
    statuses = Counter(row.get("status") for row in rows)
    values = defaultdict(list)
    answer_failures = Counter()
    citation_failures = Counter()
    affected_lines = set()

    for row in rows:
        if row.get("status") != "ok":
            continue
        blocks = [row["baseline"]] + row.get("methods", [])
        for block in blocks:
            method = block.get("method")
            failed = any(not ev.get("ok") for ev in block.get("evaluations", {}).values())
            if failed:
                answer_failures[method] += 1
                affected_lines.add(row["line"])
                if not block.get("citation_tokens"):
                    citation_failures[method] += 1
            if method == "baseline":
                continue
            for metric, evaluation in block.get("evaluations", {}).items():
                improvement = evaluation.get("target_improvement")
                if evaluation.get("ok") and improvement is not None:
                    values[(method, metric)].append(improvement)

    print(f"records={len(rows)} ok={statuses['ok']} skipped={statuses['skipped']} error={statuses['error']}")
    print(f"failed_answers={sum(answer_failures.values())} affected_queries={len(affected_lines)}")
    print("\nmethod\tmetric\tn\tmean_improvement\tpositive_rate")
    for (method, metric), metric_values in values.items():
        mean = sum(metric_values) / len(metric_values)
        positive = sum(value > 0 for value in metric_values) / len(metric_values)
        print(f"{method}\t{metric}\t{len(metric_values)}\t{mean:.6f}\t{positive:.3f}")
    print("\nmethod\tfailed_answers\tmissing_parseable_citations")
    for method in sorted(answer_failures):
        print(f"{method}\t{answer_failures[method]}\t{citation_failures[method]}")


def reconstruct_prompt(row, block, dataset_rows, max_source_chars):
    dataset_index = row["line"] - 1
    if dataset_index < 0 or dataset_index >= len(dataset_rows):
        raise ValueError(f"Dataset line {row['line']} not found")
    record = dataset_rows[dataset_index]
    if record.get("query") != row.get("query"):
        raise ValueError(
            f"Query mismatch between results and dataset on line {row['line']}"
        )
    sources = [
        oneq.source_to_text(source, "cleaned_text", "raw_text")
        for source in record["sources"]
    ]
    if block.get("method") != "baseline":
        sources[row["sugg_idx"]] = block["optimized_summary"]
    return oneq.build_answer_prompt(row["query"], sources, max_source_chars)


def inspect_row(row, block, dataset_rows, args):
    print(json.dumps({
        "status": row.get("status"),
        "line": row.get("line"),
        "query": row.get("query"),
        "method": block.get("method"),
        "target_citation": row.get("target_citation"),
        "vendor_indices": row.get("vendor_indices"),
        "citation_tokens": block.get("citation_tokens"),
        "optimization_ok": block.get("optimization_ok"),
        "optimization_error": block.get("optimization_error"),
        "evaluations": block.get("evaluations"),
        "answer_attempts": block.get("answer_attempts"),
    }, ensure_ascii=False, indent=2))
    if args.show_prompt:
        print("\n===== RECONSTRUCTED PROMPT =====\n")
        print(reconstruct_prompt(row, block, dataset_rows, args.max_source_chars))
    if args.show_answer:
        print("\n===== ANSWER =====\n")
        print(block.get("answer", ""))


def main():
    args = parse_args()
    if not args.summary and args.line is None:
        args.summary = True
    rows = read_jsonl(args.results)
    if args.summary:
        print_summary(rows)
    if args.line is not None:
        row = find_line(rows, args.line)
        if row.get("status") != "ok":
            print(json.dumps(row, ensure_ascii=False, indent=2))
            return
        block = method_block(row, args.method)
        dataset_rows = read_jsonl(args.dataset) if args.show_prompt else []
        inspect_row(row, block, dataset_rows, args)


if __name__ == "__main__":
    main()
