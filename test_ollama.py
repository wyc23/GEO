#!/usr/bin/env python3
"""
测试 Ollama 配置是否正确
"""
import os
import requests
import sys

def test_ollama_connection():
    """测试 Ollama 连接"""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "gpt-oss")
    
    print("=" * 60)
    print("测试 Ollama 配置")
    print("=" * 60)
    print(f"Ollama URL: {base_url}")
    print(f"模型: {model}")
    print()
    
    # 测试连接
    print("1. 测试 Ollama 服务连接...")
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        print("   ✓ Ollama 服务正在运行")
    except requests.exceptions.ConnectionError:
        print("   ✗ 无法连接到 Ollama 服务")
        print("   请确保 Ollama 正在运行: ollama serve")
        return False
    except Exception as e:
        print(f"   ✗ 连接错误: {e}")
        return False
    
    # 检查模型是否存在
    print(f"\n2. 检查模型 '{model}' 是否可用...")
    try:
        models = response.json()
        model_names = [m['name'] for m in models.get('models', [])]
        
        # 检查完全匹配或前缀匹配
        model_found = False
        for m in model_names:
            if m == model or m.startswith(f"{model}:"):
                model_found = True
                print(f"   ✓ 模型 '{m}' 可用")
                break
        
        if not model_found:
            print(f"   ✗ 模型 '{model}' 未找到")
            print(f"   可用模型: {', '.join(model_names)}")
            print(f"\n   请下载模型: ollama pull {model}")
            return False
            
    except Exception as e:
        print(f"   ✗ 检查模型时出错: {e}")
        return False
    
    # 测试简单生成
    print("\n3. 测试模型生成...")
    try:
        test_prompt = "Say 'Hello, GEO!' and nothing else."
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": test_prompt,
                "stream": False,
                "options": {
                    "num_predict": 20
                }
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        output = result.get('response', '').strip()
        print(f"   ✓ 模型响应: {output[:50]}...")
    except Exception as e:
        print(f"   ✗ 生成测试失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过! Ollama 配置正确。")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_ollama_connection()
    sys.exit(0 if success else 1)
