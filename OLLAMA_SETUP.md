# Ollama 配置说明

本项目已迁移至使用 Ollama 作为大语言模型提供者,替代原来的 OpenAI API。

## 前提条件

1. **安装 Ollama**
   
   访问 [Ollama官网](https://ollama.ai/) 下载并安装 Ollama。
   
   或者在 Linux 上使用以下命令安装:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **下载模型**
   
   默认使用 `gpt-oss` 模型。首次使用前需要下载:
   ```bash
   ollama pull gpt-oss
   ```
   
   你也可以选择其他模型,如:
   - `llama3.2:1b` - 更小更快的版本
   - `llama3.2:3b` - 中等大小
   - `mistral` - Mistral 7B 模型
   - `qwen2.5` - 阿里的通义千问模型
   
   下载其他模型:
   ```bash
   ollama pull <模型名称>
   ```

3. **启动 Ollama 服务**
   
   ```bash
   ollama serve
   ```
   
   默认情况下,Ollama 会在 `http://localhost:11434` 上运行。

## 环境变量配置

你可以通过环境变量来配置 Ollama 的使用:

```bash
# Ollama API 地址 (默认: http://localhost:11434)
export OLLAMA_BASE_URL="http://localhost:11434"

# 使用的模型名称 (默认: gpt-oss)
export OLLAMA_MODEL="gpt-oss"

# 其他原有的环境变量
export STATIC_CACHE="True"  # 可选
export GLOBAL_CACHE_FILE="global_cache.json"  # 可选
export GEO_CACHE_FILE="geo_optimizations_cache.json"  # 可选
```

## 使用方法

1. **安装依赖**
   ```bash
   conda create -n geo python=3.9
   conda activate geo
   pip install -r requirements.txt
   ```

2. **下载 NLTK 数据** (首次运行时)
   ```python
   python -c "import nltk; nltk.download('punkt')"
   ```

3. **配置环境变量** (可选)
   ```bash
   export OLLAMA_MODEL="gpt-oss"
   export OLLAMA_BASE_URL="http://localhost:11434"
   ```

4. **运行 GEO**
   ```bash
   cd src
   python run_geo.py
   ```

## 模型推荐

根据不同的需求选择合适的模型:

- **速度优先**: `llama3.2:1b` - 最快,但质量稍低
- **平衡**: `llama3.2` (3B) - 默认选项,速度和质量的良好平衡
- **质量优先**: `qwen2.5:7b` 或 `mistral:7b` - 更好的输出质量,但速度较慢
- **中文支持**: `qwen2.5` - 对中文的支持更好

## 代码变更说明

### 主要变更文件:

1. **src/generative_le.py** - 答案生成函数
   - 移除了 `openai` 依赖
   - 使用 Ollama HTTP API
   - 支持多次完成(num_completions)

2. **src/geo_functions.py** - GEO 优化函数
   - `call_gpt()` 函数改为使用 Ollama
   - 保留了缓存机制
   - 兼容原有的函数签名

3. **src/utils.py** - 评估函数
   - 主观印象评估改为使用 Ollama
   - 简化了评分提取逻辑

4. **requirements.txt** - 依赖包
   - 移除了 `openai<1.0.0`
   - 添加了 `requests` (用于 HTTP 调用)
   - 添加了 `nltk` (原本就需要但未列出)

## 性能对比

| 特性 | OpenAI API | Ollama |
|------|-----------|--------|
| 成本 | 付费 (按token计费) | 免费 (本地运行) |
| 速度 | 快 | 取决于硬件和模型大小 |
| 隐私 | 数据发送到 OpenAI | 完全本地,无数据泄露 |
| 网络依赖 | 需要稳定的互联网 | 可离线使用 |
| 模型选择 | 固定的 GPT 模型 | 多种开源模型可选 |

## 故障排除

### 问题: 连接错误
```
Error in calling Ollama API: Connection refused
```
**解决方案**: 确保 Ollama 服务正在运行
```bash
ollama serve
```

### 问题: 模型未找到
```
Error: model 'gpt-oss' not found
```
**解决方案**: 下载所需模型
```bash
ollama pull gpt-oss
```

### 问题: 响应超时
**解决方案**: 
1. 使用更小的模型 (如 `llama3.2:1b`)
2. 增加硬件资源
3. 减少 `num_completions` 参数

### 问题: 输出质量不佳
**解决方案**:
1. 尝试使用更大的模型 (如 `qwen2.5:7b`)
2. 调整 temperature 参数
3. 优化 prompt

## 注意事项

1. **硬件要求**: 
   - 最低: 8GB RAM (运行 1B-3B 模型)
   - 推荐: 16GB+ RAM (运行 7B 模型)
   - GPU: 可选但强烈推荐 (显著提升速度)

2. **首次运行**: 
   - 模型下载需要时间和存储空间
   - llama3.2 (3B) 约 2GB
   - 7B 模型约 4-5GB

3. **缓存机制**: 
   - 代码保留了原有的缓存机制
   - 可以通过环境变量 `STATIC_CACHE=True` 启用静态缓存

## 参考资源

- [Ollama 官方文档](https://github.com/ollama/ollama)
- [Ollama 模型库](https://ollama.ai/library)
- [原项目 README](README.md)
