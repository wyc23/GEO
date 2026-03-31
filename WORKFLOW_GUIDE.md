# GEO 代码流程说明

## 整体架构

```
查询输入 → 搜索/摘要 → LLM生成答案 → 评估引用 → GEO优化 → 重新生成 → 比较改进
```

## 核心概念

### 1. **Generative Engine (生成式引擎)**
类似于传统搜索引擎，但不返回链接列表，而是：
- 搜索相关网页
- 提取内容摘要
- 使用LLM综合生成一个完整答案
- 在答案中引用来源 [1][2][3]

### 2. **GEO (Generative Engine Optimization)**
类似于SEO，但目标是提高在LLM生成的答案中的**可见度**：
- 不改变内容的核心信息
- 通过重新表述、添加权威性、优化语言等方式
- 让LLM更倾向于引用你的内容

### 3. **Impression Score (印象分数)**
衡量一个源在生成答案中的可见度：
- 被引用的次数
- 引用的位置（开头权重更高）
- 引用时使用的词数

## 详细流程

### 阶段1: 初始化 (run_geo.py)

```python
# 加载查询
query = "What is machine learning?"
idx = 0  # 要优化的源索引
```

### 阶段2: 获取初始答案 (utils.py - get_answer)

```
get_answer(query)
    │
    ├─ 检查缓存
    │   └─ 如果有缓存，直接返回
    │
    ├─ search_handler(query)  [search_try.py]
    │   ├─ Google 搜索获取 URLs
    │   ├─ 爬取网页内容
    │   ├─ 使用 trafilatura 提取主要内容
    │   └─ 使用 Ollama 清理和总结文本
    │       └─ clean_source_gpt35()
    │
    └─ generate_answer(query, summaries)  [generative_le.py]
        ├─ 构建提示词（包含所有源摘要）
        ├─ 调用 Ollama API
        └─ 返回带引用的答案
            例: "Machine learning is a subset of AI [1]. 
                 It uses algorithms to learn from data [2][3]..."
```

### 阶段3: 计算初始印象分数

```python
# 提取引用
citations = extract_citations_new(answer)
# 结构: [[[words, sentence, [citation_numbers]], ...], ...]

# 计算分数
scores = impression_wordpos_count_simple(citations, n=5)
# 返回: [score_source1, score_source2, ..., score_source5]

# 评分公式:
# score = (词数) × exp(-位置/总数) / 引用数量
```

### 阶段4: GEO 优化循环

```python
for method_name, method_fn in GEO_METHODS.items():
    # 1. 优化目标源
    optimized_summary = method_fn(summaries[idx])
    
    # 例如 authoritative_optimization_mine:
    #   输入: "Exercise improves health."
    #   输出: "Our extensive research conclusively proves 
    #          that exercise significantly improves health."
    
    # 2. 替换摘要
    new_summaries = summaries[:idx] + [optimized_summary] + summaries[idx+1:]
    
    # 3. 重新生成答案
    new_result = get_answer(query, summaries=new_summaries, ...)
    
    # 4. 计算新分数
    new_scores = calculate_scores(new_result)
    
    # 5. 计算改进
    improvement = new_scores[idx] - init_scores[idx]
```

### 阶段5: 结果评估

```python
# 改进矩阵: [方法数 × 源数]
improvements = [
    [0.02, -0.01, 0.00, -0.01, 0.00],  # identity
    [0.15, -0.03, -0.02, -0.05, -0.05], # authoritative
    [0.08, -0.01, -0.01, -0.03, -0.03], # simple_language
    ...
]

# 成功标记: 目标源分数提升
success = improvements[:, idx] > 0
```

## GEO 优化方法详解

### 1. **authoritative_optimization_mine**
增加权威性和自信语气
```
输入: "Studies show exercise is beneficial."
输出: "Our comprehensive research definitively proves that 
       exercise provides guaranteed health benefits."
```

### 2. **simple_language_mine**
简化语言，更易理解
```
输入: "Cardiovascular endurance amelioration occurs."
输出: "Heart health improves."
```

### 3. **stats_optimization_mine**
添加统计数据和数字
```
输入: "Many people benefit from exercise."
输出: "78% of adults experience significant health improvements, 
       with a 40% reduction in disease risk."
```

### 4. **citing_credible_mine**
添加对可信来源的引用
```
输入: "Exercise helps mental health."
输出: "According to Harvard Medical School's latest study, 
       exercise significantly helps mental health."
```

## 印象评估函数

### impression_wordpos_count_simple (最常用)
```python
score = Σ (词数 × 位置权重 / 共同引用数)

位置权重 = exp(-position / total_sentences)
# 第一句: exp(0) = 1.0
# 中间句: exp(-0.5) ≈ 0.6
# 最后句: exp(-1) ≈ 0.37
```

### impression_word_count_simple
只计算词数，不考虑位置

### impression_pos_count_simple
只计算位置，不考虑词数

### impression_subjective_impression
使用 LLM 主观评估质量

## 测试脚本使用指南

### 1. **test_minimal.py** (推荐入门)
- ✓ 不需要搜索引擎
- ✓ 使用预设摘要
- ✓ 流程最简单
- ✓ 运行最快

```bash
python test_minimal.py
```

**流程:**
1. 使用 5 个预设摘要
2. 生成初始答案 (3次)
3. 优化第1个源
4. 重新生成答案
5. 比较分数改进

**预期输出:**
```
目标源 (源 1):
  初始分数:   0.2156
  优化后分数: 0.3421
  改进:       +0.1265 (+58.67%)
  ✓ 成功! 可见度提升了 58.67%
```

### 2. **test_simple_run.py**
- 需要搜索引擎 (Google)
- 实时爬取网页
- 测试完整流程
- 运行较慢

```bash
python test_simple_run.py "What is machine learning?"
```

### 3. **src/run_geo.py** (完整版)
- 使用 GEO-Bench 数据集
- 测试所有优化方法
- 生成完整结果

```bash
cd src
python run_geo.py
```

## 环境准备

### 必需:
```bash
# 1. 启动 Ollama
ollama serve

# 2. 下载模型
ollama pull llama3.2

# 3. 安装依赖
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt')"
```

### 可选环境变量:
```bash
export OLLAMA_MODEL="llama3.2"        # 或 qwen2.5, mistral
export OLLAMA_BASE_URL="http://localhost:11434"
export STATIC_CACHE="True"            # 启用缓存
export GLOBAL_CACHE_FILE="global_cache.json"
```

## 性能优化建议

### 1. 使用缓存
```bash
export STATIC_CACHE="True"
```
- 避免重复的 LLM 调用
- 大幅提升速度

### 2. 减少完成次数
```python
num_completions = 2  # 默认是5，减少可提速
```

### 3. 使用更快的模型
```bash
export OLLAMA_MODEL="llama3.2:1b"  # 1B 模型最快
```

### 4. 减少测试的方法数量
```python
# 在 run_geo.py 中只测试部分方法
GEO_METHODS = {
    'identity': identity,
    'authoritative_mine': authoritative_optimization_mine,
    # 注释掉其他方法
}
```

## 常见问题

### Q: 为什么结果有时候是负改进？
A: 这是正常的。并非所有优化都适用于所有查询。GEO研究的目标就是找出哪些方法在什么情况下有效。

### Q: 分数总是很低怎么办？
A: 
- 检查答案是否有引用标记 [1][2][3]
- 确保 Ollama 模型理解引用格式
- 可能需要调整提示词

### Q: 运行很慢怎么办？
A: 
- 使用 test_minimal.py 而不是完整版
- 减少 num_completions
- 使用更小的模型
- 启用缓存

### Q: Ollama 内存不足？
A: 
- 使用 1B 或 3B 模型
- 减少 num_predict 参数
- 关闭其他程序

## 结果解释

### 改进幅度
- **> 20%**: 显著改进
- **5-20%**: 明显改进  
- **0-5%**: 轻微改进
- **< 0%**: 负面影响

### 成功率
```
成功方法数 / 总方法数

例: 3/10 = 30% 的方法成功提升了可见度
```

## 下一步

1. **理解基础**: 运行 `test_minimal.py`
2. **测试真实查询**: 运行 `test_simple_run.py`
3. **完整评估**: 运行 `src/run_geo.py`
4. **自定义优化**: 在 `geo_functions.py` 添加新方法
5. **调整评估**: 在 `utils.py` 修改印象函数
