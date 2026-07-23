#!/bin/bash

# GEO with Ollama 快速启动脚本

echo "======================================"
echo "GEO - Generative Engine Optimization"
echo "使用 Ollama 本地大语言模型"
echo "======================================"
echo

# 检查 Ollama 是否安装
if ! command -v ollama &> /dev/null; then
    echo "错误: 未找到 Ollama"
    echo "请访问 https://ollama.ai/ 安装 Ollama"
    exit 1
fi

# 设置默认环境变量
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-gpt-oss}"

echo "配置信息:"
echo "  Ollama URL: $OLLAMA_BASE_URL"
echo "  模型: $OLLAMA_MODEL"
echo

# 检查 Ollama 服务是否运行
echo "检查 Ollama 服务..."
if curl -s "$OLLAMA_BASE_URL/api/tags" > /dev/null 2>&1; then
    echo "✓ Ollama 服务正在运行"
else
    echo "⚠ Ollama 服务未运行"
    echo "正在启动 Ollama 服务..."
    ollama serve &
    OLLAMA_PID=$!
    echo "等待服务启动..."
    sleep 3
fi

# 检查模型是否存在
echo
echo "检查模型 '$OLLAMA_MODEL'..."
if ollama list | grep -q "$OLLAMA_MODEL"; then
    echo "✓ 模型已存在"
else
    echo "模型不存在,正在下载..."
    ollama pull "$OLLAMA_MODEL"
fi

# 运行测试
echo
echo "运行配置测试..."
python test_ollama.py
if [ $? -ne 0 ]; then
    echo "配置测试失败,请检查配置"
    exit 1
fi

# 运行 GEO
echo
echo "======================================"
echo "开始运行 GEO..."
echo "======================================"
cd src
python run_geo.py

echo
echo "完成!"
