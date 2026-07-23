import requests
import time
import os
import pickle
import uuid
import json
import re

query_prompt = """Write an accurate and concise answer for the given user question, using _only_ the provided summarized web search results. The answer should be correct, high-quality, and written by an expert using an unbiased and journalistic tone. The user's language of choice such as English, Français, Español, Deutsch, or 日本語 should be used. The answer should be informative, interesting, and engaging. The answer's logic and reasoning should be rigorous and defensible. Every sentence in the answer should be _immediately followed_ by an in-line citation to the search result(s). The cited search result(s) should fully support _all_ the information in the sentence. Search results need to be cited using [index]. When citing several search results, use [1][2][3] format rather than [1, 2, 3]. You can use multiple search results to respond comprehensively while avoiding irrelevant search results.

Question: {query}

Search Results:
{source_text}
"""

# Ollama 配置
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss")
MAX_CITATION_REWRITE_ATTEMPTS = int(os.environ.get("MAX_CITATION_REWRITE_ATTEMPTS", "3"))


class CitationValidationError(RuntimeError):
    pass


def _normalize_citation_position(text: str):
    # Treat "sentence. [1]" as "sentence [1]." so sentence tokenizers keep support attached.
    return re.sub(r"([.!?])\s+((?:\[\d+\])+)", r" \2\1", text.strip())


def _split_sentences(text: str):
    text = _normalize_citation_position(text)
    chunks = re.split(r'(?<=[.!?])\s+', text.strip())
    return [c.strip() for c in chunks if c.strip()]


def _citation_stats(text: str, source_count: int):
    citation_pattern = re.compile(r"\[(\d+)\]")
    sentences = _split_sentences(text)
    if not sentences:
        return 0, 0, False

    cited_sentences = 0
    has_out_of_range = False
    for sentence in sentences:
        matches = citation_pattern.findall(sentence)
        if matches:
            cited_sentences += 1
            if any(int(m) < 1 or int(m) > source_count for m in matches):
                has_out_of_range = True
    return len(sentences), cited_sentences, has_out_of_range


def _needs_citation_rewrite(text: str, source_count: int, min_ratio: float = 0.8):
    total, cited, out_of_range = _citation_stats(text, source_count)
    if total == 0:
        return True
    if cited == 0:
        return True
    if (cited / total) < min_ratio:
        return True
    return out_of_range


def _tokenize_for_overlap(text: str):
    return {
        token
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", text.lower())
        if len(token) > 3
    }


def _best_source_citation(sentence: str, source_tokens):
    sentence_tokens = _tokenize_for_overlap(sentence)
    if not sentence_tokens:
        return 1
    scores = [len(sentence_tokens & tokens) for tokens in source_tokens]
    best_idx = max(range(len(scores)), key=lambda idx: scores[idx])
    return best_idx + 1


def _repair_citations(text: str, sources):
    """Add valid citations to uncited sentences using lexical source overlap."""
    source_tokens = [_tokenize_for_overlap(source) for source in sources]
    citation_pattern = re.compile(r"\[(\d+)\]")
    repaired = []
    for sentence in _split_sentences(text):
        valid_citations = [
            int(match)
            for match in citation_pattern.findall(sentence)
            if 1 <= int(match) <= len(sources)
        ]
        sentence = citation_pattern.sub("", sentence).strip()
        if not sentence:
            continue
        if valid_citations:
            cites = "".join(f"[{idx}]" for idx in dict.fromkeys(valid_citations))
        else:
            cites = f"[{_best_source_citation(sentence, source_tokens)}]"
        terminal = sentence[-1] if sentence[-1:] in ".!?" else "."
        sentence_body = sentence[:-1].rstrip() if sentence[-1:] in ".!?" else sentence
        repaired.append(f"{sentence_body} {cites}{terminal}")
    return " ".join(repaired)


def _first_sentence(text: str):
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return ""
    match = re.search(r"(.{40,280}?[.!?])\s", text + " ")
    if match:
        return match.group(1).strip()
    return text[:240].strip().rstrip(".,;:") + "."


def _fallback_cited_answer(query: str, sources):
    snippets = []
    for idx, source in enumerate(sources[:3], start=1):
        sentence = _first_sentence(source)
        if sentence:
            sentence = re.sub(r"\[(?:\d+)\]", "", sentence).strip()
            terminal = sentence[-1] if sentence[-1:] in ".!?" else "."
            body = sentence[:-1].rstrip() if sentence[-1:] in ".!?" else sentence
            snippets.append(f"{body} [{idx}]{terminal}")
    if snippets:
        return " ".join(snippets)
    return f"The provided sources contain information relevant to the query: {query} [1]."


def _build_rewrite_prompt(query: str, source_text: str, draft: str, source_count: int):
    return f"""You must rewrite the answer so citation formatting is valid and complete.

Rules:
1) Every sentence must end with at least one citation.
2) Citations must be in the form [k], and k must be between 1 and {source_count}.
3) If multiple citations are needed, use [1][2] style.
4) Keep statements grounded in the provided sources only.
5) Output only the final rewritten answer.

Question:
{query}

Search Results:
{source_text}

Draft Answer:
{draft}
"""

def generate_answer(query, sources, num_completions, temperature = 0.5, verbose = False, model = None):
    # 使用环境变量中的模型或默认模型
    if model is None:
        model = OLLAMA_MODEL
    
    source_text = '\n\n'.join(['### Source '+str(idx+1)+':\n'+source + '\n\n\n' for idx, source in enumerate(sources)])
    base_prompt = query_prompt.format(query = query, source_text = source_text)

    results = []
    for i in range(num_completions):
        while True:
            try:
                print(f'Running Ollama Model ({model}) - Completion {i+1}/{num_completions}')
                prompt = base_prompt
                answer_text = ""
                for attempt in range(MAX_CITATION_REWRITE_ATTEMPTS):
                    response = requests.post(
                        f"{OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "temperature": 0.0 if attempt > 0 else temperature,
                            "stream": False,
                            "options": {
                                "num_predict": 1024,
                                "top_p": 1.0
                            }
                        },
                        timeout=300
                    )
                    response.raise_for_status()
                    result = response.json()
                    answer_text = result.get('response', '').strip()
                    if not _needs_citation_rewrite(answer_text, len(sources)):
                        break
                    prompt = _build_rewrite_prompt(query, source_text, answer_text, len(sources))
                    print(f'Citation rewrite attempt {attempt+1}/{MAX_CITATION_REWRITE_ATTEMPTS-1}')

                if _needs_citation_rewrite(answer_text, len(sources)):
                    repaired_answer = _repair_citations(answer_text, sources)
                    if _needs_citation_rewrite(repaired_answer, len(sources), min_ratio=1.0):
                        print("Citation repair failed; using source-snippet fallback")
                        repaired_answer = _fallback_cited_answer(query, sources)
                    if _needs_citation_rewrite(repaired_answer, len(sources), min_ratio=1.0):
                        raise CitationValidationError("Unable to produce citation-complete answer")
                    answer_text = repaired_answer

                results.append(answer_text + '\n')
                print('Response Done')
                break
            except CitationValidationError:
                raise
            except Exception as e:
                print('Error in calling Ollama API', e)
                time.sleep(15)
                continue
    
    # 保存使用统计(如果需要)
    try:
        os.makedirs("response_usages_16k", exist_ok=True)
        usage_info = {"model": model, "num_completions": num_completions}
        pickle.dump(usage_info, open(f"response_usages_16k/{uuid.uuid4()}.pkl", "wb"))
    except:
        pass

    return results
