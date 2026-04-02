#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
from typing import List, Dict, Tuple


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from search_try import search_handler  # noqa: E402


TECH_KEYWORDS = {
    "api", "python", "linux", "database", "model", "llm", "machine learning",
    "neural", "kubernetes", "docker", "cloud", "algorithm", "encryption",
}

SENSITIVE_KEYWORDS = {
    "suicide", "self-harm", "bomb", "weapon", "terror", "hate", "exploit",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a GEO-bench-like JSONL dataset from custom queries."
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Single query. Can be provided multiple times.",
    )
    parser.add_argument(
        "--query-file",
        type=str,
        help="Text file with one query per line.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="geo_bench_like.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--sources-per-query",
        type=int,
        default=5,
        help="Number of sources to collect per query.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sugg_idx generation.",
    )
    parser.add_argument(
        "--fixed-sugg-idx",
        type=int,
        default=None,
        help="If set, use this fixed sugg_idx for every query.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately on first query failure.",
    )
    parser.add_argument(
        "--product-query-json",
        type=str,
        help="Path to product_queries.json. If set, build B2B/B2C datasets from it.",
    )
    parser.add_argument(
        "--segment",
        choices=["B2B", "B2C", "both"],
        default="both",
        help="Which segment(s) to export when using --product-query-json.",
    )
    parser.add_argument(
        "--out-b2b",
        type=str,
        default="geo_bench_like_b2b.jsonl",
        help="Output JSONL path for B2B when using --product-query-json.",
    )
    parser.add_argument(
        "--out-b2c",
        type=str,
        default="geo_bench_like_b2c.jsonl",
        help="Output JSONL path for B2C when using --product-query-json.",
    )
    return parser.parse_args()


def load_queries(cli_queries: List[str], query_file: str = None) -> List[str]:
    queries = [q.strip() for q in cli_queries if q.strip()]
    if query_file:
        with open(query_file, "r", encoding="utf-8") as f:
            for line in f:
                q = line.strip()
                if q:
                    queries.append(q)
    # deduplicate while preserving order
    deduped = list(dict.fromkeys(queries))
    return deduped


def infer_tags(query: str) -> List[str]:
    ql = query.lower()
    tags = ["informational", "research"]
    tags.append("question" if "?" in query else "command")
    tags.append("technical" if any(k in ql for k in TECH_KEYWORDS) else "non-technical")
    tags.append("sensitive" if any(k in ql for k in SENSITIVE_KEYWORDS) else "non-sensitive")
    tags.append("simple" if len(query.split()) <= 8 else "intermediate")
    tags.append("fact")
    return tags


def build_record(query: str, source_count: int, fixed_sugg_idx=None) -> Dict:
    result = search_handler(query, source_count=source_count)
    sources = result.get("sources", [])
    if len(sources) == 0:
        raise ValueError("No sources fetched.")

    bench_sources = []
    for s in sources:
        bench_sources.append(
            {
                "raw_text": s.get("raw_source", s.get("source", "")),
                "url": s.get("url", ""),
                "cleaned_text": s.get("source", s.get("summary", "")),
            }
        )

    if fixed_sugg_idx is not None:
        if fixed_sugg_idx < 0 or fixed_sugg_idx >= len(bench_sources):
            raise ValueError(
                f"fixed_sugg_idx={fixed_sugg_idx} out of range for {len(bench_sources)} sources"
            )
        sugg_idx = fixed_sugg_idx
    else:
        sugg_idx = random.randint(0, len(bench_sources) - 1)

    return {
        "query": query,
        "tags": infer_tags(query),
        "sources": bench_sources,
        "sugg_idx": sugg_idx,
    }


def load_product_query_entries(product_query_json: str, segment: str) -> Tuple[List[Dict], List[Dict]]:
    with open(product_query_json, "r", encoding="utf-8") as f:
        products = json.load(f)

    b2b_entries = []
    b2c_entries = []
    for item in products:
        product = item.get("product", "")
        user_intent = item.get("user_intent", "")
        decision_complexity = item.get("decision_complexity", "")
        technical_level = item.get("technical_level", "")
        query_map = item.get("queries", {})

        for stage, stage_map in query_map.items():
            for q in stage_map.get("B2B", []):
                b2b_entries.append(
                    {
                        "query": q,
                        "segment": "B2B",
                        "product": product,
                        "journey_stage": stage,
                        "user_intent": user_intent,
                        "decision_complexity": decision_complexity,
                        "technical_level": technical_level,
                    }
                )
            for q in stage_map.get("B2C", []):
                b2c_entries.append(
                    {
                        "query": q,
                        "segment": "B2C",
                        "product": product,
                        "journey_stage": stage,
                        "user_intent": user_intent,
                        "decision_complexity": decision_complexity,
                        "technical_level": technical_level,
                    }
                )

    if segment == "B2B":
        return b2b_entries, []
    if segment == "B2C":
        return [], b2c_entries
    return b2b_entries, b2c_entries


def build_tag_list_from_entry(entry: Dict) -> List[str]:
    base = infer_tags(entry["query"])
    enriched = base + [
        entry["segment"].lower(),
        entry["journey_stage"].lower(),
        entry["user_intent"],
        entry["decision_complexity"],
        entry["technical_level"],
    ]
    return list(dict.fromkeys(enriched))


def process_entries_to_jsonl(
    entries: List[Dict],
    out_path: str,
    source_count: int,
    fixed_sugg_idx,
    fail_fast: bool,
):
    if not entries:
        return (0, 0, 0)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    success = 0
    failed = 0
    total = len(entries)

    with open(out_path, "w", encoding="utf-8") as out_f:
        for i, entry in enumerate(entries, 1):
            query = entry["query"]
            print(f"[{i}/{total}] [{entry['segment']}] {entry['product']} | {entry['journey_stage']}")
            try:
                record = build_record(
                    query=query,
                    source_count=source_count,
                    fixed_sugg_idx=fixed_sugg_idx,
                )
                record["tags"] = build_tag_list_from_entry(entry)
                record["segment"] = entry["segment"]
                record["product"] = entry["product"]
                record["journey_stage"] = entry["journey_stage"]
                record["user_intent"] = entry["user_intent"]
                record["decision_complexity"] = entry["decision_complexity"]
                record["technical_level"] = entry["technical_level"]
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                success += 1
                print(f"  ✓ sources={len(record['sources'])}, sugg_idx={record['sugg_idx']}")
            except Exception as e:
                failed += 1
                print(f"  ✗ failed: {e}")
                if fail_fast:
                    raise

    return success, failed, total


def main():
    args = parse_args()
    random.seed(args.seed)

    if args.product_query_json:
        b2b_entries, b2c_entries = load_product_query_entries(args.product_query_json, args.segment)
        overall_success = 0
        overall_failed = 0
        overall_total = 0

        if b2b_entries:
            s, f, t = process_entries_to_jsonl(
                entries=b2b_entries,
                out_path=args.out_b2b,
                source_count=args.sources_per_query,
                fixed_sugg_idx=args.fixed_sugg_idx,
                fail_fast=args.fail_fast,
            )
            overall_success += s
            overall_failed += f
            overall_total += t
            print(f"\nB2B Output: {args.out_b2b} | Success={s}, Failed={f}, Total={t}")

        if b2c_entries:
            s, f, t = process_entries_to_jsonl(
                entries=b2c_entries,
                out_path=args.out_b2c,
                source_count=args.sources_per_query,
                fixed_sugg_idx=args.fixed_sugg_idx,
                fail_fast=args.fail_fast,
            )
            overall_success += s
            overall_failed += f
            overall_total += t
            print(f"\nB2C Output: {args.out_b2c} | Success={s}, Failed={f}, Total={t}")

        print("\nDone.")
        print(f"Overall Success: {overall_success}, Failed: {overall_failed}, Total: {overall_total}")
        return

    queries = load_queries(args.query, args.query_file)
    if not queries:
        raise SystemExit("No queries provided. Use --query/--query-file or --product-query-json.")

    success, failed, total = process_entries_to_jsonl(
        entries=[
            {
                "query": q,
                "segment": "generic",
                "product": "",
                "journey_stage": "generic",
                "user_intent": "research",
                "decision_complexity": "intermediate",
                "technical_level": "non-technical",
            }
            for q in queries
        ],
        out_path=args.out,
        source_count=args.sources_per_query,
        fixed_sugg_idx=args.fixed_sugg_idx,
        fail_fast=args.fail_fast,
    )
    print("\nDone.")
    print(f"Output: {args.out}")
    print(f"Success: {success}, Failed: {failed}, Total: {total}")


if __name__ == "__main__":
    main()
