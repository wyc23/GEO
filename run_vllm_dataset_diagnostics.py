#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import run_vllm_onequery_full_diagnostics as oneq  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="Run vLLM GEO diagnostics for a local JSONL dataset.")
    parser.add_argument("--dataset", default="geo_bench_like_b2b.jsonl")
    parser.add_argument("--output-jsonl", default="vllm_qwen36_b2b_dataset_diagnostics.jsonl")
    parser.add_argument("--output-md", default="vllm_qwen36_b2b_dataset_summary.md")
    parser.add_argument("--base-url", default=oneq.VLLM_BASE_URL)
    parser.add_argument("--model", default=oneq.VLLM_MODEL)
    parser.add_argument("--source-field", default="cleaned_text")
    parser.add_argument("--fallback-source-field", default="raw_text")
    parser.add_argument("--vendor-results", default="cleaned_text_only_results.jsonl")
    parser.add_argument("--require-vendor-target", action="store_true")
    parser.add_argument("--vendor-seed", type=int, default=42)
    parser.add_argument("--start-line", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--append", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep completed/skipped rows, discard error rows, and continue missing lines.",
    )
    parser.add_argument("--metrics", default="simple_wordpos,simple_word,simple_pos")
    parser.add_argument("--answer-max-tokens", type=int, default=4096)
    parser.add_argument("--optimization-max-tokens", type=int, default=4096)
    parser.add_argument("--eval-max-tokens", type=int, default=64)
    parser.add_argument("--answer-temperature", type=float, default=0.5)
    parser.add_argument("--optimization-temperature", type=float, default=0.0)
    parser.add_argument("--eval-temperature", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-source-chars", type=int, default=5000)
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def iter_records(path, start_line, limit):
    emitted = 0
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if line_no < start_line:
                continue
            if limit is not None and emitted >= limit:
                break
            line = line.strip()
            if not line:
                continue
            emitted += 1
            yield line_no, json.loads(line)


def load_vendor_targets(path):
    vendor_by_query = {}
    if not path:
        return vendor_by_query
    vendor_path = Path(path)
    if not vendor_path.exists():
        raise FileNotFoundError(f"Vendor results file not found: {path}")
    with vendor_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("is_vendor_owned_product") is True:
                query = row.get("query", "")
                rank = row.get("source_rank")
                if isinstance(rank, int) and rank > 0:
                    vendor_by_query.setdefault(query, set()).add(rank - 1)
    return {query: sorted(indices) for query, indices in vendor_by_query.items()}


def validate_record(record, source_field, fallback_source_field, vendor_by_query=None, require_vendor_target=False, vendor_seed=42, line_no=0):
    query = (record.get("query") or "").strip()
    sources = record.get("sources") or []
    original_idx = record.get("sugg_idx", -1)
    idx = original_idx
    texts = [oneq.source_to_text(s, source_field, fallback_source_field) for s in sources]
    vendor_indices = [i for i in (vendor_by_query or {}).get(query, []) if 0 <= i < len(sources)]
    reasons = []
    if not query:
        reasons.append("empty_query")
    if not sources:
        reasons.append("no_sources")
    empty_positions = [i for i, text in enumerate(texts) if not text]
    if empty_positions:
        reasons.append(f"empty_source_text:{empty_positions}")
    if require_vendor_target:
        if not vendor_indices:
            reasons.append("no_vendor_owned_source")
        else:
            rng = random.Random(vendor_seed + line_no)
            idx = rng.choice(vendor_indices)
            if idx in empty_positions:
                reasons.append(f"selected_vendor_source_empty:{idx}")
    elif not isinstance(idx, int) or idx < 0 or idx >= len(sources):
        reasons.append("bad_idx")
    return reasons, query, texts, idx, original_idx, vendor_indices


def append_jsonl(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def load_jsonl(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    rows = sorted(rows, key=lambda row: row.get("line", 0))
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def summarize_rows(rows):
    method_names = []
    metric_names = []
    method_metric_values = {}
    answer_failures = []
    metric_failures = []
    valid_count = 0
    skipped_count = 0
    for row in rows:
        if row.get("status") == "skipped":
            skipped_count += 1
            continue
        if row.get("status") != "ok":
            answer_failures.append((row.get("line"), "record", row.get("error")))
            continue
        valid_count += 1
        for method_block in row.get("methods", []):
            method = method_block.get("method")
            if method not in method_names:
                method_names.append(method)
            for metric, ev in method_block.get("evaluations", {}).items():
                if metric not in metric_names:
                    metric_names.append(metric)
                if ev.get("ok") and ev.get("target_improvement") is not None:
                    method_metric_values.setdefault((method, metric), []).append(ev["target_improvement"])
                elif not ev.get("ok"):
                    metric_failures.append((row.get("line"), f"{method}/{metric}", ev.get("error")))
            if any(not ev.get("ok") for ev in method_block.get("evaluations", {}).values()):
                errors = sorted({
                    str(ev.get("error"))
                    for ev in method_block.get("evaluations", {}).values()
                    if not ev.get("ok")
                })
                answer_failures.append((row.get("line"), method, ", ".join(errors)))
    lines = [
        "# vLLM Qwen3.6 Dataset Diagnostics Summary",
        "",
        f"- Completed valid records: {valid_count}",
        f"- Skipped invalid records: {skipped_count}",
        f"- Failed method answers: {len(answer_failures)}",
        f"- Failed metric entries: {len(metric_failures)}",
        "",
        "## Mean Target Improvement",
        "",
        "| Method | Metric | N | Mean | Positive Rate |",
        "|---|---|---:|---:|---:|",
    ]
    for method in method_names:
        for metric in metric_names:
            vals = method_metric_values.get((method, metric), [])
            if not vals:
                continue
            mean = sum(vals) / len(vals)
            pos = sum(1 for v in vals if v > 0) / len(vals)
            lines.append(f"| `{method}` | `{metric}` | {len(vals)} | {mean:.6f} | {pos:.3f} |")
    if answer_failures:
        lines.extend(["", "## Failed Method Answers", "", "| Line | Method | Error |", "|---:|---|---|"])
        for line, context, error in answer_failures:
            lines.append(f"| {line} | `{str(context).replace('|','/')}` | `{str(error).replace('|','/')}` |")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    metrics = oneq.select_metrics(args.metrics)
    output_jsonl = Path(args.output_jsonl)
    output_md = Path(args.output_md)
    if args.resume and args.append:
        raise ValueError("--resume and --append cannot be used together")
    if args.resume:
        existing_rows = load_jsonl(output_jsonl)
        rows_for_summary = [
            row for row in existing_rows
            if row.get("status") in {"ok", "skipped"}
        ]
        completed_lines = {row.get("line") for row in rows_for_summary}
        write_jsonl(output_jsonl, rows_for_summary)
        print(
            f"Resuming with {len(completed_lines)} completed/skipped lines; "
            f"discarded {len(existing_rows) - len(rows_for_summary)} error rows",
            flush=True,
        )
    else:
        rows_for_summary = []
        completed_lines = set()
    if not args.append and not args.resume:
        output_jsonl.write_text("", encoding="utf-8")
    vendor_by_query = load_vendor_targets(args.vendor_results) if args.require_vendor_target else {}
    optimization_llm_log = []
    oneq.patch_geo_functions(
        args.model,
        args.base_url,
        args.retries,
        args.optimization_max_tokens,
        args.optimization_temperature,
        optimization_llm_log,
    )

    started_at = time.time()
    for line_no, record in iter_records(args.dataset, args.start_line, args.limit):
        if line_no in completed_lines:
            print(f"Skipping completed line {line_no}", flush=True)
            continue
        reasons, query, sources, idx, original_idx, vendor_indices = validate_record(
            record,
            args.source_field,
            args.fallback_source_field,
            vendor_by_query=vendor_by_query,
            require_vendor_target=args.require_vendor_target,
            vendor_seed=args.vendor_seed,
            line_no=line_no,
        )
        print(f"\n=== line {line_no}: {query[:100]} ===", flush=True)
        if args.require_vendor_target and not reasons:
            print(f"Selected vendor target idx={idx} rank={idx + 1}; candidates={[i + 1 for i in vendor_indices]}", flush=True)
        if reasons:
            row = {
                "status": "skipped",
                "line": line_no,
                "query": query,
                "reasons": reasons,
                "sugg_idx": record.get("sugg_idx"),
                "vendor_indices": vendor_indices,
                "num_sources": len(record.get("sources") or []),
            }
            append_jsonl(output_jsonl, row)
            rows_for_summary.append(row)
            print(f"Skipped: {reasons}", flush=True)
            continue
        try:
            baseline_prompt = oneq.build_answer_prompt(query, sources, args.max_source_chars)
            print("Generating baseline answer", flush=True)
            baseline_answer, baseline_attempts = oneq.vllm_chat(
                messages=[{"role": "user", "content": baseline_prompt}],
                model=args.model,
                base_url=args.base_url,
                temperature=args.answer_temperature,
                max_tokens=args.answer_max_tokens,
                retries=args.retries,
                purpose=f"line{line_no}:baseline_answer",
            )
            print("Evaluating baseline", flush=True)
            baseline_evaluations = oneq.evaluate_all(
                baseline_answer, query, metrics, len(sources), idx,
                args.model, args.base_url, args.retries, args.eval_max_tokens, args.eval_temperature,
            )
            row = {
                "status": "ok",
                "line": line_no,
                "query": query,
                "sugg_idx": idx,
                "original_sugg_idx": original_idx,
                "vendor_indices": vendor_indices,
                "target_citation": idx + 1,
                "num_sources": len(sources),
                "model": args.model,
                "base_url": args.base_url,
                "metrics": metrics,
                "source_lengths": [len(s) for s in sources],
                "source_urls": [s.get("url", "") for s in record.get("sources", [])],
                "baseline": {
                    "method": "baseline",
                    "answer": baseline_answer,
                    "answer_attempts": baseline_attempts,
                    "citation_tokens": oneq.citation_tokens(baseline_answer),
                    "target_summary": sources[idx],
                    "evaluations": baseline_evaluations,
                },
                "methods": [],
            }
            for method, fn in oneq.GEO_METHODS.items():
                print(f"Running method {method}", flush=True)
                method_block = {
                    "method": method,
                    "optimization_ok": True,
                    "optimization_error": None,
                    "optimized_summary": sources[idx],
                }
                if method != "identity":
                    try:
                        method_block["optimized_summary"] = fn(sources[idx])
                    except Exception as exc:
                        method_block["optimization_ok"] = False
                        method_block["optimization_error"] = repr(exc)
                method_sources = sources[:idx] + [method_block["optimized_summary"]] + sources[idx + 1:]
                try:
                    answer_prompt = oneq.build_answer_prompt(query, method_sources, args.max_source_chars)
                    answer, answer_attempts = oneq.vllm_chat(
                        messages=[{"role": "user", "content": answer_prompt}],
                        model=args.model,
                        base_url=args.base_url,
                        temperature=args.answer_temperature,
                        max_tokens=args.answer_max_tokens,
                        retries=args.retries,
                        purpose=f"line{line_no}:answer:{method}",
                    )
                    method_block.update({
                        "answer": answer,
                        "answer_attempts": answer_attempts,
                        "citation_tokens": oneq.citation_tokens(answer),
                    })
                    print(f"Evaluating method {method}", flush=True)
                    evaluations = oneq.evaluate_all(
                        answer, query, metrics, len(sources), idx,
                        args.model, args.base_url, args.retries, args.eval_max_tokens, args.eval_temperature,
                    )
                    oneq.add_improvements(evaluations, baseline_evaluations)
                    method_block["evaluations"] = evaluations
                except Exception as exc:
                    method_block.update({
                        "answer": "",
                        "answer_attempts": [],
                        "citation_tokens": [],
                        "answer_error": repr(exc),
                        "evaluations": {m: {"ok": False, "error": repr(exc)} for m in metrics},
                    })
                row["methods"].append(method_block)
            append_jsonl(output_jsonl, row)
            rows_for_summary.append(row)
            output_md.write_text(summarize_rows(rows_for_summary), encoding="utf-8")
            elapsed = time.time() - started_at
            print(f"Finished line {line_no} in elapsed {elapsed/60:.1f} min", flush=True)
        except Exception as exc:
            row = {"status": "error", "line": line_no, "query": query, "error": repr(exc)}
            append_jsonl(output_jsonl, row)
            rows_for_summary.append(row)
            output_md.write_text(summarize_rows(rows_for_summary), encoding="utf-8")
            print(f"ERROR line {line_no}: {exc!r}", flush=True)
            if args.fail_fast:
                raise
    rows_for_summary.sort(key=lambda row: row.get("line", 0))
    write_jsonl(output_jsonl, rows_for_summary)
    output_md.write_text(summarize_rows(rows_for_summary), encoding="utf-8")
    print(f"Wrote {output_jsonl}", flush=True)
    print(f"Wrote {output_md}", flush=True)


if __name__ == "__main__":
    main()
