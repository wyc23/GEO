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

## 下一步建议

下一轮正式实验应先确定两个实验设计问题：

1. 是否将 answer temperature 设为 0，或者每个条件生成多次后取均值，以降低
   baseline/identity 的随机波动。
2. 是否把 `[Source N]` 规范化为 `[N]`。若规范化，应在新结果中明确标记，不能静默
   修改本轮已提交的原始结果。
