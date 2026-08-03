# GEO 当前交接说明

当前稳定主线是在自有 B2B 数据集上，通过自部署 vLLM 的 `qwen3.6-27b` 运行 GEO。
旧 Ollama、DeepSeek、SJTU 和单 query 诊断代码已不再作为当前实验入口。

## 当前正式实验

- 输入：`geo_bench_like_b2b.jsonl`
- Vendor 判定：`cleaned_text_only_results.jsonl`
- 入口：`run_vllm_dataset_diagnostics.py`
- 共享生成和评分逻辑：`run_vllm_onequery_full_diagnostics.py`
- 完整结果：`vllm_qwen36_b2b_vendor_simple_diagnostics.jsonl`
- 汇总：`vllm_qwen36_b2b_vendor_simple_summary.md`
- 结果说明：`EXPERIMENT_RESULTS_GUIDE.md`
- 检查工具：`analyze_vllm_results.py`

## 当前结果

- 数据集共 160 条 query。
- 100 条满足 vendor-owned target 和 source 非空要求并完成实验。
- 60 条跳过。
- 每条有效 query 生成 1 个 baseline 和 10 个 improve answer。
- 本轮只运行非主观 citation evaluation：
  `simple_wordpos`、`simple_word`、`simple_pos`。
- 三项指标上平均提升最高的方法均为 `stats_optimization_gpt`。

结果解释时必须注意：

1. `identity` 也重新生成 answer，且 answer temperature 为 0.5，因此非零 improvement
   包含模型采样波动。
2. 47 个 method answer 存在引用格式错误，三个 metric 会对同一个 answer分别报错。
3. 主要错误是模型输出 `[Source 1]`，而当前解析器只接受 `[1]`。
4. 汇总均值只包含该方法、该指标计算成功的样本，比较方法时应同时查看 `N`。

详细字段、重跑命令、prompt 重建方法和文件哈希见
`EXPERIMENT_RESULTS_GUIDE.md`。

## B2C Vendor Filter

B2C 的 source 级 vendor-information 分类已经完成：

- 输入：`geo_bench_like_b2c.jsonl`，160 条 query、1600 个 source。
- 分类模型：HT vLLM 上的 `qwen3.6-27b`，temperature 0、thinking 关闭。
- 分类结果：`cleaned_text_only_results_b2c.jsonl`。
- 汇总：`b2c_vendor_filter_summary.md` 和 `b2c_vendor_filter_summary.json`。
- 442 个 source 判为 vendor-linked，1158 个判为 false。
- 122 条 query 满足至少一个 vendor-linked source 且所有 source 非空。
- 37 条因为没有 vendor-linked source 跳过，1 条因为存在空 source 跳过。
- 1600 条分类无错误、无缺失、无重复，全部一次请求成功。

这里的 `is_vendor_owned_product` 沿用 B2B prompt 的历史字段名，实际含义是正文中存在
明确的 product-vendor/brand 关联；第三方页面也可能为 true，并非严格的网页所有权判定。
此外 B2B 标签由 `gpt-oss` 生成，B2C 标签由 Qwen 生成，因此两组 vendor 比例不应直接
解释为 segment 本身的差异。

## 下一步建议

下一轮正式实验应先确定两个实验设计问题：

1. 是否将 answer temperature 设为 0，或者每个条件生成多次后取均值，以降低
   baseline/identity 的随机波动。
2. 是否把 `[Source N]` 规范化为 `[N]`。若规范化，应在新结果中明确标记，不能静默
   修改本轮已提交的原始结果。
3. 使用 `cleaned_text_only_results_b2c.jsonl` 作为 `--vendor-results`，对 122 条 eligible
   B2C query 运行与 B2B 相同的 improve 和 simple evaluation。
