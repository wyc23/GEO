#!/usr/bin/env python3
"""Validate source labels and build the eligible-query list for a GEO run."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output-md")
    parser.add_argument("--output-json")
    return parser.parse_args()


def read_jsonl(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def analyze(dataset, labels):
    labels_by_key = defaultdict(list)
    for label in labels:
        key = (label.get("query"), label.get("source_rank"), label.get("url"))
        labels_by_key[key].append(label)

    eligible = []
    skipped = []
    missing_labels = []
    duplicate_labels = []
    true_sources = 0
    error_sources = 0

    for line_no, record in enumerate(dataset, start=1):
        query = record.get("query", "")
        sources = record.get("sources") or []
        vendor_ranks = []
        empty_ranks = []
        query_errors = []
        for rank, source in enumerate(sources, start=1):
            text = (source.get("cleaned_text") or source.get("raw_text") or "").strip()
            if not text:
                empty_ranks.append(rank)
            key = (query, rank, source.get("url", "") or "")
            matches = labels_by_key.get(key, [])
            if not matches:
                missing_labels.append({"line": line_no, "source_rank": rank, "url": key[2]})
                continue
            if len(matches) > 1:
                duplicate_labels.append({"line": line_no, "source_rank": rank, "count": len(matches)})
            label = matches[-1]
            if label.get("error") is not None:
                error_sources += 1
                query_errors.append(rank)
            if label.get("is_vendor_owned_product") is True:
                true_sources += 1
                vendor_ranks.append(rank)

        reasons = []
        if not vendor_ranks:
            reasons.append("no_vendor_linked_source")
        if empty_ranks:
            reasons.append("empty_source_text")
        if query_errors:
            reasons.append("classification_error")
        if any(item["line"] == line_no for item in missing_labels):
            reasons.append("missing_label")
        item = {
            "line": line_no,
            "product": record.get("product", ""),
            "query": query,
            "vendor_source_ranks": vendor_ranks,
            "empty_source_ranks": empty_ranks,
            "classification_error_ranks": query_errors,
        }
        if reasons:
            item["reasons"] = reasons
            skipped.append(item)
        else:
            eligible.append(item)

    return {
        "dataset_records": len(dataset),
        "expected_sources": sum(len(record.get("sources") or []) for record in dataset),
        "label_rows": len(labels),
        "true_sources": true_sources,
        "false_sources": len(labels) - true_sources,
        "error_sources": error_sources,
        "missing_labels": missing_labels,
        "duplicate_labels": duplicate_labels,
        "eligible_queries": eligible,
        "skipped_queries": skipped,
    }


def to_markdown(result):
    reason_counts = Counter(
        reason
        for row in result["skipped_queries"]
        for reason in row.get("reasons", [])
    )
    lines = [
        "# Vendor Filter Summary",
        "",
        f"- Dataset records: {result['dataset_records']}",
        f"- Expected sources: {result['expected_sources']}",
        f"- Label rows: {result['label_rows']}",
        f"- Vendor-linked sources: {result['true_sources']}",
        f"- Non-vendor-linked sources: {result['false_sources']}",
        f"- Classification errors: {result['error_sources']}",
        f"- Missing labels: {len(result['missing_labels'])}",
        f"- Duplicate labels: {len(result['duplicate_labels'])}",
        f"- Eligible queries: {len(result['eligible_queries'])}",
        f"- Skipped queries: {len(result['skipped_queries'])}",
        "",
        "## Skip Reasons",
        "",
        "| Reason | Queries |",
        "|---|---:|",
    ]
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"| `{reason}` | {count} |")
    lines.extend([
        "",
        "## Eligible Queries",
        "",
        "| Line | Product | Vendor Source Ranks | Query |",
        "|---:|---|---|---|",
    ])
    for row in result["eligible_queries"]:
        query = row["query"].replace("|", "/")
        ranks = ", ".join(map(str, row["vendor_source_ranks"]))
        lines.append(f"| {row['line']} | {row['product']} | {ranks} | {query} |")
    return "\n".join(lines) + "\n"


def main():
    args = parse_args()
    result = analyze(read_jsonl(args.dataset), read_jsonl(args.labels))
    summary = to_markdown(result)
    print(summary, end="")
    if args.output_md:
        Path(args.output_md).write_text(summary, encoding="utf-8")
    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
