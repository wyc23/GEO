#!/usr/bin/env python3
"""Classify dataset sources for explicit product-vendor information."""

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


DEFAULT_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:18001/v1")
DEFAULT_MODEL = os.environ.get("VLLM_MODEL", "qwen3.6-27b")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="geo_bench_like_b2b.jsonl")
    parser.add_argument("--output", default="cleaned_text_only_results.jsonl")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--truncate-chars", type=int, default=12000)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--start-line", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def build_system_prompt(product):
    # Keep this prompt aligned with the B2B labels for cross-segment comparison.
    return f"""
You are a strict classifier for brand-linked {product} presence.

Task:
Decide whether the provided cleaned_text clearly shows a {product} together with its corresponding brand / vendor / manufacturer information.

Return valid JSON only:
{{
  "is_vendor_owned_product": true,
  "label": "vendor_owned_product",
  "reason": "short reason"
}}

Labels:
- "vendor_owned_product"
- "not_vendor_owned_product"

Decision rule:
Return true if the cleaned_text clearly contains BOTH:
1) a concrete {product} or service
2) brand / vendor / manufacturer / company information corresponding to that {product} or service

Return false if:
- the text mentions only a {product} category with no brand information
- the text mentions only a brand/company with no concrete {product} or service
- the text is too vague, sparse, or ambiguous to link a {product} to a brand
- the text is generic corporate, editorial, discussion, or informational text without a clear product-brand connection

Important:
- A third-party page can still be true if the cleaned_text clearly shows a {product} and its corresponding brand information.
- The {product} and brand information must be clearly linked in the cleaned_text itself.

Examples of false:
- "smartphone deals"
- "Apple company news"
- "best laptops in 2026"
- "customer support options"
- any text without a clear product-brand link

Reason:
- Keep it short and factual.
- State whether a clear product-brand link is present or missing.

Default:
Return false unless cleaned_text clearly shows a concrete product/service and its corresponding brand/vendor/manufacturer information.
""".strip()


def build_user_prompt(product, query, source_rank, input_value):
    return f"""
Can you check whether the following content is brand-owned {product} (or {product} vendor) content or not?
Can you check whether it belongs to vendor-owned {product}:

PRODUCT:
{product}

QUERY:
{query}

SOURCE RANK:
{source_rank}

INPUT TYPE:
cleaned_text

INPUT VALUE:
{input_value}
""".strip()


def parse_json_response(content):
    content = (content or "").strip()
    if not content:
        raise ValueError("empty_response")
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            return json.loads(content[start:end + 1])
        raise


def normalize_result(parsed, error=None):
    is_vendor = parsed.get("is_vendor_owned_product")
    if isinstance(is_vendor, str):
        is_vendor = is_vendor.strip().lower() in {"true", "1", "yes"}
    elif not isinstance(is_vendor, bool):
        is_vendor = False
    label = parsed.get("label")
    if label not in {"vendor_owned_product", "not_vendor_owned_product"}:
        label = "vendor_owned_product" if is_vendor else "not_vendor_owned_product"
    reason = parsed.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "fallback: model output parse failed or missing required fields."
    return {
        "is_vendor_owned_product": is_vendor,
        "label": label,
        "reason": reason.strip(),
        "error": error,
    }


def classify_source(item, args):
    text = item["cleaned_text"][:args.truncate_chars]
    if not text:
        result = normalize_result({}, error="empty_input")
        return {**item, **result, "model": args.model, "attempts": []}

    messages = [
        {"role": "system", "content": build_system_prompt(item["product"])},
        {"role": "user", "content": build_user_prompt(
            item["product"], item["query"], item["source_rank"], text
        )},
    ]
    attempts = []
    last_error = None
    last_content = ""
    for attempt in range(1, args.retries + 1):
        started = time.time()
        try:
            response = requests.post(
                f"{args.base_url.rstrip('/')}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": args.model,
                    "messages": messages,
                    "temperature": 0,
                    "max_tokens": args.max_tokens,
                    "stream": False,
                    "response_format": {"type": "json_object"},
                    "chat_template_kwargs": {"enable_thinking": False},
                },
                timeout=args.timeout,
            )
            body = response.json()
            meta = {
                "attempt": attempt,
                "status_code": response.status_code,
                "wall_seconds": round(time.time() - started, 3),
            }
            if response.status_code >= 400:
                meta["error"] = body
                attempts.append(meta)
                response.raise_for_status()
            choice = (body.get("choices") or [{}])[0]
            last_content = ((choice.get("message") or {}).get("content") or "").strip()
            meta["finish_reason"] = choice.get("finish_reason")
            meta["usage"] = body.get("usage") or {}
            attempts.append(meta)
            parsed = parse_json_response(last_content)
            return {
                **item,
                **normalize_result(parsed),
                "model": args.model,
                "attempts": attempts,
            }
        except Exception as exc:
            last_error = repr(exc)
            if not attempts or attempts[-1].get("attempt") != attempt:
                attempts.append({
                    "attempt": attempt,
                    "error": last_error,
                    "wall_seconds": round(time.time() - started, 3),
                })
            time.sleep(min(attempt, 3))

    error = last_error or "classification_failed"
    if last_content:
        error += f" | raw={last_content[:180]}"
    return {
        **item,
        **normalize_result({}, error=error),
        "model": args.model,
        "attempts": attempts,
    }


def item_key(item):
    return (item.get("query"), item.get("source_rank"), item.get("url"))


def load_completed(path):
    completed = set()
    if not path.exists():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                completed.add(item_key(json.loads(line)))
    return completed


def iter_items(path, start_line, limit):
    emitted = 0
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if line_no < start_line:
                continue
            if limit is not None and emitted >= limit:
                break
            if not line.strip():
                continue
            emitted += 1
            record = json.loads(line)
            for source_rank, source in enumerate(record.get("sources") or [], start=1):
                yield {
                    "dataset_line": line_no,
                    "product": record.get("product", ""),
                    "query": record.get("query", ""),
                    "source_rank": source_rank,
                    "input_type": "cleaned_text",
                    "url": source.get("url", "") or "",
                    "cleaned_text": source.get("cleaned_text", "") or "",
                }


def append_jsonl(path, record):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()


def sort_output(path):
    with path.open("r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    rows.sort(key=lambda row: (row.get("dataset_line", 0), row.get("source_rank", 0)))
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1")
    output = Path(args.output)
    if args.overwrite:
        output.write_text("", encoding="utf-8")
    completed = load_completed(output)
    items = [
        item for item in iter_items(args.input, args.start_line, args.limit)
        if item_key(item) not in completed
    ]
    print(f"Already completed: {len(completed)}", flush=True)
    print(f"Pending sources: {len(items)}", flush=True)

    finished = 0
    true_count = 0
    error_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(classify_source, item, args): item for item in items}
        for future in as_completed(futures):
            result = future.result()
            append_jsonl(output, result)
            finished += 1
            true_count += result["is_vendor_owned_product"] is True
            error_count += result.get("error") is not None
            if finished % 25 == 0 or finished == len(items):
                print(
                    f"Finished {finished}/{len(items)}; true={true_count}; errors={error_count}",
                    flush=True,
                )
    sort_output(output)
    print(f"Saved classifications to {output}", flush=True)


if __name__ == "__main__":
    main()
