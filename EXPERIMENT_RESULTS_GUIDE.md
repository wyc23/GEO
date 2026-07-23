# vLLM B2B GEO 实验结果说明

本文说明如何阅读、复核和重跑当前保留的正式实验。

## 文件对应关系

| 角色 | 文件 | 用途 |
|---|---|---|
| 主输入 | `geo_bench_like_b2b.jsonl` | 160 条 query，每条包含 10 个已抓取 source |
| Vendor 判定 | `cleaned_text_only_results.jsonl` | 按 query 和 `source_rank` 标记 `is_vendor_owned_product` |
| 数据集入口 | `run_vllm_dataset_diagnostics.py` | 过滤 query、选择 vendor target、依次运行 baseline 和所有 improve |
| 单条核心逻辑 | `run_vllm_onequery_full_diagnostics.py` | 构造 prompt、调用 vLLM、运行 evaluation |
| Improve 定义 | `src/run_geo.py` | `GEO_METHODS` 列出本次运行的 10 种 improve |
| Improve 实现 | `src/geo_functions.py` | 每种 improve 的 prompt 和处理逻辑 |
| Answer prompt | `src/generative_le.py` | 原始 `query_prompt` 模板 |
| Evaluation | `src/utils.py` | 三个 simple citation metric 的计算 |
| 原始结果 | `vllm_qwen36_b2b_vendor_simple_diagnostics.jsonl` | 每条输入对应一行完整结果 |
| 汇总结果 | `vllm_qwen36_b2b_vendor_simple_summary.md` | 方法级平均 improvement、成功率和失败 answer |
| 分析工具 | `analyze_vllm_results.py` | 汇总结果，查看 answer，重建某次调用的 prompt |

## 实验配置

正式实验使用：

- 模型：`qwen3.6-27b`
- 接口：OpenAI-compatible vLLM API
- answer `temperature=0.5`
- improve `temperature=0.0`
- answer 和 improve 的 `max_tokens=4096`
- 每个 source 最多进入 prompt 5000 字符
- evaluation：`simple_wordpos`、`simple_word`、`simple_pos`
- vendor target 随机种子：42
- Qwen thinking：关闭

运行命令：

```bash
python run_vllm_dataset_diagnostics.py \
  --dataset geo_bench_like_b2b.jsonl \
  --require-vendor-target \
  --vendor-results cleaned_text_only_results.jsonl \
  --vendor-seed 42 \
  --metrics simple_wordpos,simple_word,simple_pos \
  --output-jsonl vllm_qwen36_b2b_vendor_simple_diagnostics.jsonl \
  --output-md vllm_qwen36_b2b_vendor_simple_summary.md \
  --base-url http://127.0.0.1:18001/v1 \
  --model qwen3.6-27b \
  --answer-max-tokens 4096 \
  --optimization-max-tokens 4096
```

`127.0.0.1:18001` 是运行时建立的 SSH tunnel 本地端口，不是模型机器的永久地址。

## Query 和 target 如何筛选

程序从 `cleaned_text_only_results.jsonl` 读取 vendor 判定。只有至少一个
`is_vendor_owned_product == true` 的 query 才有资格运行。

对每条有效 query：

1. 根据 query 找到所有 vendor-owned `source_rank`。
2. 用 `Random(42 + dataset_line)` 从候选 source 中选择一个 target。
3. `sugg_idx` 是选中的零基 target 下标。
4. `target_citation` 是对应的一基引用编号，即 `sugg_idx + 1`。
5. 任意 source 正文为空时整条 query 跳过。

本次 160 条输入中，100 条完成、60 条跳过、0 条发生整条运行错误。

## JSONL 顶层怎么看

JSONL 不是一个 JSON 数组，而是每行一个独立 JSON object。`line` 对应输入数据集的
原始行号。

跳过记录主要字段：

```json
{
  "status": "skipped",
  "line": 3,
  "query": "...",
  "reasons": ["no_vendor_owned_source"],
  "vendor_indices": [],
  "num_sources": 10
}
```

完成记录主要字段：

| 字段 | 含义 |
|---|---|
| `line` | 原始数据集行号 |
| `query` | 本条问题 |
| `sugg_idx` | 本次实际优化的 source，下标从 0 开始 |
| `original_sugg_idx` | 数据集原先提供的 target，不用于本次 vendor target 实验 |
| `vendor_indices` | 所有 vendor-owned source 的零基下标 |
| `target_citation` | answer 中 target 对应的引用号，从 1 开始 |
| `source_urls` | 10 个 source 的 URL，顺序就是引用编号顺序 |
| `baseline` | 未修改 source 时生成的 answer 和评分 |
| `methods` | 10 种 improve 各自的优化 source、answer 和评分 |

## Baseline 和 method block

`baseline.answer` 是使用原始 10 个 source 生成的回答。`baseline.target_summary`
是原始 target source。

每个 `methods[]` 元素代表一次独立实验：

| 字段 | 含义 |
|---|---|
| `method` | improve 方法名 |
| `optimization_ok` | target source 是否成功完成 improve |
| `optimized_summary` | improve 后替换进 prompt 的 target source |
| `answer` | 替换 target 后重新生成的完整回答 |
| `answer_attempts` | HTTP 状态、token usage、耗时和 finish reason |
| `citation_tokens` | 从 answer 中按 `[(数字)]` 解析到的引用 |
| `evaluations` | 三种 simple metric 的结果 |

除 target source 外，其余 9 个 source 在 baseline 和 method 之间不变。

## Evaluation 字段

每个 evaluation 包含：

| 字段 | 含义 |
|---|---|
| `ok` | answer 是否有可解析且不越界的引用，并成功计算指标 |
| `scores` | 10 个 source 分别获得的归一化 exposure 分数 |
| `target_score` | `scores[sugg_idx]` |
| `target_improvement` | method target score 减 baseline target score |
| `success` | `target_improvement > 0` |
| `error` | 失败原因 |

三个指标的区别：

- `simple_word`：引用获得的文本位置按回答词数计算。
- `simple_pos`：更强调引用出现的位置。
- `simple_wordpos`：同时考虑词数和位置。

这里的 improvement 是一次 method answer 与一次 baseline answer 的差。因为
`temperature=0.5`，即使 `identity` 没有修改 source，两次独立生成也可能不同；
因此 `identity` 的非零均值代表生成随机性，不能解释为优化效果。

## Missing citation 说明

`missing_or_invalid_citations` 按 metric 记录，所以同一个坏 answer 会让三项 metric
各失败一次。原始 JSONL 中的 141 个 metric failure 实际对应 47 个 method answer。
如果把 baseline 也计入，1100 个 answer 中共有 52 个引用失败。

其中 51 个使用了 `[Source 1]` 形式，而解析器要求 `[1]`；另有 1 个引用编号越界。
这是模型格式遵循问题，不是 `max_tokens` 截断。

## 常用检查命令

查看总体统计：

```bash
python analyze_vllm_results.py --summary
```

查看第 2 行 `stats_optimization_gpt` 的元数据和 answer：

```bash
python analyze_vllm_results.py \
  --line 2 \
  --method stats_optimization_gpt \
  --show-answer
```

重建同一次生成所使用的完整 user prompt：

```bash
python analyze_vllm_results.py \
  --line 2 \
  --method stats_optimization_gpt \
  --show-prompt
```

dataset runner 为控制结果文件体积，没有重复保存每个完整 answer prompt。重建是确定性的：
读取原始 10 个 source，把 target 替换为结果中的 `optimized_summary`，每个 source截至
5000 字符，再填入 `src/generative_le.py` 的 `query_prompt`。

## 文件完整性

本次提交时的 SHA-256：

```text
geo_bench_like_b2b.jsonl
4101aee4373815094f64839e9315cd0a70bfc18bf1d3ed3e5f73f2db1114105c

cleaned_text_only_results.jsonl
5fe32a2bcbe8ba1eac625b716d3526fa5cf99841ace519ee035c768bbbd0815c

vllm_qwen36_b2b_vendor_simple_diagnostics.jsonl
3a23882f1b95f61c9ed55c2cd01ed6740e45c6d7a04afb2275d77707b5339a3e
```
