#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
import time
from glob import glob
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import geo_functions  # noqa: E402
from generative_le import query_prompt  # noqa: E402
from run_geo import GEO_METHODS, IMPRESSION_FNS  # noqa: E402
from utils import extract_citations_new, impression_wordpos_count_simple, impression_word_count_simple, impression_pos_count_simple  # noqa: E402

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:18000/v1")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "qwen3.6-27b")
SIMPLE_METRICS = {
    "simple_wordpos": impression_wordpos_count_simple,
    "simple_word": impression_word_count_simple,
    "simple_pos": impression_pos_count_simple,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run one GEO query with all LLM calls routed to local vLLM.")
    parser.add_argument("--dataset", default="geo_bench_like_b2b.jsonl")
    parser.add_argument("--line", type=int, default=1)
    parser.add_argument("--source-field", default="cleaned_text")
    parser.add_argument("--fallback-source-field", default="raw_text")
    parser.add_argument("--output-json", default="onequery_vllm_qwen36_full_diagnostics.json")
    parser.add_argument("--output-md", default="onequery_vllm_qwen36_full_diagnostics.md")
    parser.add_argument("--base-url", default=VLLM_BASE_URL)
    parser.add_argument("--model", default=VLLM_MODEL)
    parser.add_argument("--answer-max-tokens", type=int, default=4096)
    parser.add_argument("--optimization-max-tokens", type=int, default=4096)
    parser.add_argument("--eval-max-tokens", type=int, default=64)
    parser.add_argument("--answer-temperature", type=float, default=0.5)
    parser.add_argument("--optimization-temperature", type=float, default=0.0)
    parser.add_argument("--eval-temperature", type=float, default=0.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-source-chars", type=int, default=5000)
    parser.add_argument("--metrics", default="all", help="Comma-separated metric names, or 'all'.")
    return parser.parse_args()


def vllm_chat(messages, model, base_url, temperature, max_tokens, retries, purpose):
    attempts = []
    last_body = None
    for attempt in range(1, retries + 1):
        started = time.time()
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
                "max_tokens": max_tokens,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=600,
        )
        meta = {"attempt": attempt, "purpose": purpose, "status_code": response.status_code}
        try:
            body = response.json()
        except Exception:
            body = {"raw_text": response.text[:4000]}
        last_body = body
        meta["body_keys"] = sorted(body.keys()) if isinstance(body, dict) else []
        meta["wall_seconds"] = round(time.time() - started, 3)
        if response.status_code >= 400:
            meta["error"] = body
            attempts.append(meta)
            time.sleep(min(2 * attempt, 10))
            continue
        choice = (body.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = (message.get("content") or "").strip()
        meta["finish_reason"] = choice.get("finish_reason")
        meta["usage"] = body.get("usage") or {}
        meta["content_chars"] = len(content)
        attempts.append(meta)
        if content:
            return content, attempts
        time.sleep(min(2 * attempt, 10))
    raise RuntimeError(f"vLLM returned no content for {purpose}: {last_body}")


def load_record(path, line_no):
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i == line_no:
                return json.loads(line)
    raise ValueError(f"Line {line_no} not found in {path}")


def source_to_text(source, primary, fallback):
    return (source.get(primary) or source.get(fallback) or source.get("summary") or source.get("source") or "").strip()


def build_answer_prompt(query, sources, max_source_chars):
    source_text = "\n\n".join(
        "### Source " + str(idx + 1) + ":\n" + source[:max_source_chars] + "\n\n\n"
        for idx, source in enumerate(sources)
    )
    return query_prompt.format(query=query, source_text=source_text)


def citation_tokens(answer):
    return [int(x) for x in re.findall(r"\[(\d+)\]", answer or "")]


def valid_citations(tokens, n_sources):
    return bool(tokens) and all(1 <= token <= n_sources for token in tokens)


def get_summary_from_optimization_response(text):
    tex = text.replace("```\n```", "```")
    b = tex.rfind("```")
    if b != -1:
        if tex.count("```") < 2:
            a = b + 3
            b = -1
        else:
            a = tex[:b].rfind("```") + 3
    else:
        a = -1
    if b - a < 50:
        a = b if len(tex) - b > 200 else a
        b = -1
    if a <= 2:
        a = 0
    if b != -1:
        new_tex = tex[a:b].strip()
    else:
        new_tex = tex[a:].strip()
    if new_tex.lower().startswith("updated"):
        new_tex = "\n".join(new_tex.splitlines()[1:])
    return new_tex or text


def patch_geo_functions(model, base_url, retries, max_tokens, temperature, llm_log):
    def call_vllm_gpt(user_prompt, system_prompt=geo_functions.COMMON_SYSTEM_PROMPT, model=None, temperature=0.0, num_completions=1, regenerte_answer=False, pre_msgs=None):
        user_content = user_prompt
        if pre_msgs is not None:
            pre_msgs_text = "\n".join([msg.get("content", "") for msg in pre_msgs])
            user_content = pre_msgs_text + "\n\n" + user_prompt
        content, attempts = vllm_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=model or VLLM_MODEL,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            retries=retries,
            purpose="optimization",
        )
        parsed = get_summary_from_optimization_response(content)
        llm_log.append({
            "purpose": "optimization",
            "user_prompt_chars": len(user_prompt),
            "system_prompt_chars": len(system_prompt or ""),
            "raw_response": content,
            "parsed_response": parsed,
            "attempts": attempts,
        })
        return parsed

    geo_functions.call_gpt = call_vllm_gpt


def evaluate_simple(answer, metric, n_sources, idx):
    tokens = citation_tokens(answer)
    if not valid_citations(tokens, n_sources):
        return {"ok": False, "error": "missing_or_invalid_citations", "citation_tokens": tokens}
    scores = SIMPLE_METRICS[metric](extract_citations_new(answer), n_sources)
    return {"ok": True, "scores": scores, "target_score": scores[idx], "citation_tokens": tokens}


def parse_score(text):
    match = re.search(r"[1-5](?:\.[0-9]+)?", text or "")
    if not match:
        return 3.0
    return max(min(5.0, float(match.group())), 1.0)


def evaluate_subjective_bundle(answer, query, n_sources, idx, model, base_url, retries, max_tokens, temperature):
    prompt_scores = {}
    prompt_outputs = {}
    for prompt_file in sorted(glob(str(ROOT_DIR / "geval_prompts" / "*.txt"))):
        name = Path(prompt_file).stem
        print(f"    eval prompt {name}", flush=True)
        prompt = Path(prompt_file).read_text(encoding="utf-8")
        prompt = prompt.replace("[1]", f"[{idx + 1}]")
        cur_prompt = prompt.format(query=query, answer=answer)
        content, attempts = vllm_chat(
            messages=[{"role": "user", "content": cur_prompt}],
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            retries=retries,
            purpose=f"eval:{name}",
        )
        prompt_scores[name] = parse_score(content)
        prompt_outputs[name] = {"raw_response": content, "attempts": attempts}
    return prompt_scores, prompt_outputs


def subjective_result_from_bundle(metric, prompt_scores, prompt_outputs, n_sources, idx):
    if metric == "subjective_score":
        target_score = sum(prompt_scores.values()) / len(prompt_scores) if prompt_scores else 0
    else:
        target_score = prompt_scores.get(metric, 3.0)
    scores = [target_score if i == idx else 0 for i in range(n_sources)]
    return {
        "ok": True,
        "scores": scores,
        "target_score": target_score,
        "prompt_scores": prompt_scores,
        "prompt_outputs": prompt_outputs,
    }


def evaluate_all(answer, query, metrics, n_sources, idx, model, base_url, retries, eval_max_tokens, eval_temperature):
    results = {}
    subjective_metrics = [metric for metric in metrics if metric not in SIMPLE_METRICS]
    for metric in metrics:
        if metric not in SIMPLE_METRICS:
            continue
        print(f"    eval {metric}", flush=True)
        try:
            results[metric] = evaluate_simple(answer, metric, n_sources, idx)
        except Exception as exc:
            results[metric] = {"ok": False, "error": repr(exc), "citation_tokens": citation_tokens(answer)}
    if subjective_metrics:
        print("    eval subjective bundle", flush=True)
        try:
            prompt_scores, prompt_outputs = evaluate_subjective_bundle(
                answer, query, n_sources, idx, model, base_url, retries, eval_max_tokens, eval_temperature
            )
            for metric in subjective_metrics:
                results[metric] = subjective_result_from_bundle(metric, prompt_scores, prompt_outputs, n_sources, idx)
        except Exception as exc:
            for metric in subjective_metrics:
                results[metric] = {"ok": False, "error": repr(exc), "citation_tokens": citation_tokens(answer)}
    return results


def select_metrics(metric_arg):
    if metric_arg == "all":
        return list(IMPRESSION_FNS.keys())
    metrics = [item.strip() for item in metric_arg.split(",") if item.strip()]
    unknown = [metric for metric in metrics if metric not in IMPRESSION_FNS]
    if unknown:
        raise ValueError(f"Unknown metric(s): {', '.join(unknown)}")
    return metrics


def add_improvements(evaluations, baseline_evaluations):
    for metric, result in evaluations.items():
        base = baseline_evaluations.get(metric, {})
        if result.get("ok") and base.get("ok"):
            result["target_improvement"] = result["target_score"] - base["target_score"]
            result["success"] = result["target_improvement"] > 0
        else:
            result["target_improvement"] = None
            result["success"] = None


def markdown_summary(data):
    lines = [
        "# vLLM Qwen One Query Full Diagnostics",
        "",
        f"- Query: {data['query']}",
        f"- Target citation: [{data['target_citation']}]",
        f"- Model: `{data['model']}`",
        f"- Base URL: `{data['base_url']}`",
        f"- Sources: {data['num_sources']}",
        "",
        "## Score Summary",
        "",
        "| Method | Metric | Status | Target Score | Improvement | Success | Error |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for block in [data["baseline"]] + data["methods"]:
        method = block["method"]
        for metric, ev in block["evaluations"].items():
            status = "ok" if ev.get("ok") else "failed"
            lines.append(
                f"| `{method}` | `{metric}` | {status} | {ev.get('target_score', '')} | {ev.get('target_improvement', '')} | {ev.get('success', '')} | {ev.get('error', '')} |"
            )
    lines.extend(["", "## Raw Answers And Optimized Sources", ""])
    for block in [data["baseline"]] + data["methods"]:
        lines.extend([
            f"### Method: `{block['method']}`",
            "",
            f"- Answer chars: {len(block.get('answer', ''))}",
            f"- Citation tokens: `{block.get('citation_tokens', [])}`",
            "",
            "#### Optimized Target Source",
            "",
            "```text",
            block.get("optimized_summary", ""),
            "```",
            "",
            "#### Raw Answer",
            "",
            "```text",
            block.get("answer", ""),
            "```",
            "",
        ])
    return "\n".join(lines)


def main():
    args = parse_args()
    record = load_record(args.dataset, args.line)
    query = record["query"]
    sources = [source_to_text(s, args.source_field, args.fallback_source_field) for s in record["sources"]]
    idx = int(record["sugg_idx"])
    metrics = select_metrics(args.metrics)
    optimization_llm_log = []
    patch_geo_functions(args.model, args.base_url, args.retries, args.optimization_max_tokens, args.optimization_temperature, optimization_llm_log)

    data = {
        "dataset": args.dataset,
        "line": args.line,
        "query": query,
        "sugg_idx": idx,
        "target_citation": idx + 1,
        "num_sources": len(sources),
        "model": args.model,
        "base_url": args.base_url,
        "source_lengths": [len(s) for s in sources],
        "source_urls": [s.get("url", "") for s in record["sources"]],
        "metrics": metrics,
        "methods": [],
        "optimization_llm_log": optimization_llm_log,
    }

    print("Generating baseline answer", flush=True)
    baseline_prompt = build_answer_prompt(query, sources, args.max_source_chars)
    baseline_answer, baseline_attempts = vllm_chat(
        messages=[{"role": "user", "content": baseline_prompt}],
        model=args.model,
        base_url=args.base_url,
        temperature=args.answer_temperature,
        max_tokens=args.answer_max_tokens,
        retries=args.retries,
        purpose="baseline_answer",
    )
    print("Evaluating baseline", flush=True)
    baseline_evaluations = evaluate_all(
        baseline_answer, query, metrics, len(sources), idx,
        args.model, args.base_url, args.retries, args.eval_max_tokens, args.eval_temperature,
    )
    data["baseline"] = {
        "method": "baseline",
        "answer_prompt": baseline_prompt,
        "answer": baseline_answer,
        "answer_attempts": baseline_attempts,
        "citation_tokens": citation_tokens(baseline_answer),
        "optimized_summary": sources[idx],
        "evaluations": baseline_evaluations,
    }

    for method, fn in GEO_METHODS.items():
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
            answer_prompt = build_answer_prompt(query, method_sources, args.max_source_chars)
            answer, answer_attempts = vllm_chat(
                messages=[{"role": "user", "content": answer_prompt}],
                model=args.model,
                base_url=args.base_url,
                temperature=args.answer_temperature,
                max_tokens=args.answer_max_tokens,
                retries=args.retries,
                purpose=f"answer:{method}",
            )
            method_block.update({
                "answer_prompt": answer_prompt,
                "answer": answer,
                "answer_attempts": answer_attempts,
                "citation_tokens": citation_tokens(answer),
            })
            print(f"Evaluating method {method}", flush=True)
            evaluations = evaluate_all(
                answer, query, metrics, len(sources), idx,
                args.model, args.base_url, args.retries, args.eval_max_tokens, args.eval_temperature,
            )
            add_improvements(evaluations, baseline_evaluations)
            method_block["evaluations"] = evaluations
        except Exception as exc:
            method_block.update({
                "answer_prompt": method_block.get("answer_prompt", ""),
                "answer": "",
                "answer_attempts": [],
                "citation_tokens": [],
                "answer_error": repr(exc),
                "evaluations": {m: {"ok": False, "error": repr(exc)} for m in metrics},
            })
        data["methods"].append(method_block)
        Path(args.output_json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        Path(args.output_md).write_text(markdown_summary(data), encoding="utf-8")

    Path(args.output_json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(args.output_md).write_text(markdown_summary(data), encoding="utf-8")
    print(f"Wrote {args.output_json}", flush=True)
    print(f"Wrote {args.output_md}", flush=True)


if __name__ == "__main__":
    main()
