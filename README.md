# GEO: Generative Engine Optimization

## Current B2B vLLM Experiment

The current reproducible experiment runs all GEO improve methods and the three
non-subjective citation metrics on vendor-owned targets from the local B2B
dataset.

- Start with `HANDOFF.md` for the current project state.
- Read `EXPERIMENT_RESULTS_GUIDE.md` for the result schema, experiment command,
  code-to-result mapping, caveats, and inspection examples.
- Run `python analyze_vllm_results.py --summary` to verify the committed result.

<div class="badge-container">
    <a href="https://generative-engines.com/GEO/" class="badge">
        <img src="https://img.shields.io/website?down_message=down&style=for-the-badge&up_message=up&url=https%3A%2F%2Fgenerative-engines.com/" alt="Website">
    </a>
    <a href="https://huggingface.co/datasets/GEO-optim/geo-bench" class="badge">
        <img src="https://img.shields.io/badge/Dataset-GEO-%2DBENCH-orange?style=for-the-badge" alt="Dataset">
    </a>
    <a href="https://arxiv.org/abs/2311.09735" class="badge">
        <img src="https://img.shields.io/badge/arXiv-2311.09735-red.svg?style=for-the-badge" alt="Arxiv Paper">
    </a>
    <a href="https://huggingface.co/spaces/GEO-optim/geo-bench" class="badge">
        <img src="https://img.shields.io/badge/Leaderboard-GEO-%2DBENCH-green?style=for-the-badge" alt="Code">
    </a>
</div>

## TLDR

**GEO** introduces optimization techniques to boost website visibility in generative engine responses.

## Abstract
> The advent of large language models (LLMs) has ushered in a new paradigm of search engines that use generative models to gather and summarize information to answer user queries. These Generative Engines are reshaping search engines, promising personalized and precise responses to user queries. Yet, content creators grapple with a lack of control over how their content appears in these engines. Enter GENERATIVE ENGINE OPTIMIZATION (GEO), a solution that empowers content creators with a set of optimization strategies to enhance their online visibility. To evaluate GEO, we introduce GEO-BENCH, a collection of diverse user queries from different sources, each tagged with relevant categories and corresponding search resutls. Our experiments reveal that GEO can boost source visibility by up to 40%, offering practical insights for content creators. GEO heralds a new era in information discovery systems, promising profound implications for both search engine developers and content creators
>

![GEO-Teaser](docs/GEO/static/images/geo_teaser.png)


## Installation

1. Create a conda environment: conda create -n geo python=3.9
2. conda activate geo
3. pip install -r requirements.txt

### Using Ollama (New Default)

This project now uses Ollama for local LLM inference. See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for detailed setup instructions.

**Quick Start:**
1. Install Ollama: https://ollama.ai/
2. Pull a model: `ollama pull gpt-oss`
3. Start Ollama: `ollama serve`
4. (Optional) Set environment variables:
   ```bash
   export OLLAMA_MODEL="gpt-oss"
   export OLLAMA_BASE_URL="http://localhost:11434"
   ```

## Run GEO

To replicate results in paper, simply run:
```python
cd src
python run_geo.py
```

## Define new GEO functions

You can define custom GEO functions in `src/geo_functions.py`. Reference them in `src/run_geo.py` in `GEO_METHODS` variable, to evaluate on your new custom GEO function. 

## GEO-BENCH

GEO-bench is hosted on huggingface, can be downloaded using:
```python
from datasets import load_dataset
load_dataset('GEO-optim/geo-bench')
``` 

### Build a GEO-bench-like dataset from your own queries

Use `build_geo_bench_like_dataset.py` to generate GEO-bench-style JSONL:

- Core fields: `query`, `tags`, `sources` (`raw_text`, `url`, `cleaned_text`), `sugg_idx`
- Source pipeline: DuckDuckGo search + webpage extraction + Ollama cleaning

Manual query mode:

```bash
python build_geo_bench_like_dataset.py \
  --query "What is machine learning?" \
  --out geo_bench_like.jsonl \
  --sources-per-query 5
```

`product_query/product_queries.json` mode (B2B/B2C split):

```bash
python build_geo_bench_like_dataset.py \
  --product-query-json product_query/product_queries.json \
  --segment both \
  --out-b2b geo_bench_like_b2b.jsonl \
  --out-b2c geo_bench_like_b2c.jsonl \
  --sources-per-query 5
```

Optional proxy:

```bash
export http_proxy=http://127.0.0.1:7897
export https_proxy=http://127.0.0.1:7897
```

Notes:

- `--segment` supports `B2B`, `B2C`, or `both`.
- In product-query mode, each record also includes:
  `segment`, `product`, `journey_stage`, `user_intent`, `decision_complexity`, `technical_level`.

## Leaderboard

Leaderboard is available at: [https://huggingface.co/spaces/Pranjal2041/GEO-bench](leaderboard)

## Citation

```
@misc{aggarwal2023geo,
      title={GEO: Generative Engine Optimization}, 
      author={Pranjal Aggarwal and Vishvak Murahari and Tanmay Rajpurohit and Ashwin Kalyan and Karthik R Narasimhan and Ameet Deshpande},
      year={2023},
      eprint={2311.09735},
      archivePrefix={arXiv},
      primaryClass={cs.LG}
}
```
