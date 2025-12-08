import requests
import time
import os
import pickle
import uuid
import json

query_prompt = """Write an accurate and concise answer for the given user question, using _only_ the provided summarized web search results. The answer should be correct, high-quality, and written by an expert using an unbiased and journalistic tone. The user's language of choice such as English, Français, Español, Deutsch, or 日本語 should be used. The answer should be informative, interesting, and engaging. The answer's logic and reasoning should be rigorous and defensible. Every sentence in the answer should be _immediately followed_ by an in-line citation to the search result(s). The cited search result(s) should fully support _all_ the information in the sentence. Search results need to be cited using [index]. When citing several search results, use [1][2][3] format rather than [1, 2, 3]. You can use multiple search results to respond comprehensively while avoiding irrelevant search results.

Question: {query}

Search Results:
{source_text}
"""

# Ollama 配置
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

def generate_answer(query, sources, num_completions, temperature = 0.5, verbose = False, model = None):
    # 使用环境变量中的模型或默认模型
    if model is None:
        model = OLLAMA_MODEL
    
    source_text = '\n\n'.join(['### Source '+str(idx+1)+':\n'+source + '\n\n\n' for idx, source in enumerate(sources)])
    prompt = query_prompt.format(query = query, source_text = source_text)

    results = []
    for i in range(num_completions):
        while True:
            try:
                print(f'Running Ollama Model ({model}) - Completion {i+1}/{num_completions}')
                response = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
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
                results.append(result['response'] + '\n')
                print('Response Done')
                break
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