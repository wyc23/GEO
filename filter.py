import json
import os
import time
from pathlib import Path
import re

import requests


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss")
MAX_RETRIES = 3
TRUNCATE_CHARS = 12000

INPUT_FILES = [
    "./geo_bench_like_b2b.jsonl",
]

OUTPUT_FILE_CLEANED_TEXT = "./cleaned_text_only_results.jsonl"

GROUP_SIZE = 16
TARGET_GROUP = 9
LINES_TO_EXTRACT = 3
PROCESS_ALL_RECORDS = True

def build_system_prompt(product):
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

def iter_selected_records(path, start_line=None, end_line=None):
    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if start_line is not None and line_number < start_line:
                continue
            if end_line is not None and line_number > end_line:
                break

            line = line.strip()
            if not line:
                continue

            yield line_number, json.loads(line)


def truncate_text(text, max_chars=TRUNCATE_CHARS):
    return text[:max_chars]


def extract_source_fields(source):
    return {
        "url": source.get("url", "") or "",
        "cleaned_text": source.get("cleaned_text", "") or "",
    }


def build_user_prompt(product, query, source_rank, input_type, input_value):
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
{input_type}

INPUT VALUE:
{input_value}
""".strip()


def _parse_json_from_response(content: str):
    content = (content or "").strip()
    if not content:
        raise ValueError("empty_response")

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        pass

    # Fallback: extract first JSON object block
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(content[start:end + 1])

    raise ValueError("invalid_json_response")


def _normalize_result(parsed, source_rank, input_type, error=None):
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
        "source_rank": source_rank,
        "input_type": input_type,
        "is_vendor_owned_product": is_vendor,
        "label": label,
        "reason": reason.strip(),
        "error": error,
    }


def classify_input(product, query, source_rank, input_type, input_value):
    input_value = truncate_text(input_value)

    if not input_value:
        return _normalize_result(
            parsed={},
            source_rank=source_rank,
            input_type=input_type,
            error="empty_input",
        )

    user_prompt = build_user_prompt(
        product=product,
        query=query,
        source_rank=source_rank,
        input_type=input_type,
        input_value=input_value,
    )
    system_prompt = build_system_prompt(product)

    last_error = None
    last_content = ""
    for _ in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "format": "json",
                    "stream": False,
                    "options": {
                        "temperature": 0,
                    },
                },
                timeout=60,
            )
            response.raise_for_status()
            body = response.json()
            content = (
                body.get("message", {}).get("content", "")
                or body.get("response", "")
                or ""
            ).strip()
            last_content = content
            parsed = _parse_json_from_response(content)
            return _normalize_result(parsed, source_rank=source_rank, input_type=input_type)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(1)

    return _normalize_result(
        parsed={},
        source_rank=source_rank,
        input_type=input_type,
        error=(last_error or "classification_failed") + (f" | raw={last_content[:180]}" if last_content else ""),
    )


def append_jsonl(record, path):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def reset_output_file(path):
    output_path = Path(path)
    if output_path.exists():
        output_path.unlink()


def run_pipeline(input_type, output_file):
    if PROCESS_ALL_RECORDS:
        start_line = None
        end_line = None
    else:
        start_line = (TARGET_GROUP - 1) * GROUP_SIZE + 1
        end_line = start_line + LINES_TO_EXTRACT - 1

    reset_output_file(output_file)

    for input_file in INPUT_FILES:
        for line_number, record in iter_selected_records(input_file, start_line, end_line):
            query = record.get("query", "")
            product = record.get("product", "")
            sources = record.get("sources", [])

            for source_rank, source in enumerate(sources, start=1):
                fields = extract_source_fields(source)
                input_value = fields[input_type]
                result = classify_input(
                    product=product,
                    query=query,
                    source_rank=source_rank,
                    input_type=input_type,
                    input_value=input_value,
                )

                append_jsonl(
                    {
                        "product": product,
                        "query": query,
                        "reason": result.get("reason"),
                        "source_rank": source_rank,
                        "input_type": input_type,
                        "url": fields["url"],
                        input_type: input_value,
                        "is_vendor_owned_product": result.get("is_vendor_owned_product"),
                        "label": result.get("label"),
                        "error": result.get("error"),
                    },
                    output_file,
                )

    print(f"Saved {input_type} matches to: {output_file}")
    if PROCESS_ALL_RECORDS:
        print("Processed line range: all")
    else:
        print(f"Processed line range: {start_line}-{end_line}")


def main():
    run_pipeline("cleaned_text", OUTPUT_FILE_CLEANED_TEXT)


if __name__ == "__main__":
    main()
