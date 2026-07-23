#!/usr/bin/env python3
"""
简化的GEO测试脚本 - 使用单个查询测试完整流程
"""
import sys
import os
import json

# 初始化缓存文件和 NLTK 数据
def init_caches():
    """创建必需的缓存文件"""
    cache_files = [
        'global_cache.json',
        'gpt-eval-scores-cache_new-new.json',
        'geo_optimizations_cache.json',
    ]
    for cache_file in cache_files:
        if not os.path.exists(cache_file):
            with open(cache_file, 'w') as f:
                json.dump({}, f)
    
    # 创建必要的目录
    for dir_name in ['response_usages', 'response_usages_16k']:
        os.makedirs(dir_name, exist_ok=True)
    
    # 下载必需的 NLTK 数据
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
    except:
        pass

# 初始化
init_caches()

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils import get_answer, extract_citations_new, impression_wordpos_count_simple
from geo_functions import authoritative_optimization_mine, simple_language_mine
import json

def simple_test(query="What is machine learning?"):
    """
    使用单个查询测试GEO流程
    
    Args:
        query: 要测试的查询问题
    """
    print("=" * 70)
    print("GEO 简化测试")
    print("=" * 70)
    print(f"查询: {query}")
    print()
    
    # Step 1: 获取初始答案和源
    print("Step 1: 获取初始答案...")
    print("-" * 70)
    
    try:
        # 从搜索获取答案（会调用搜索引擎和Ollama）
        result = get_answer(query, num_completions=2, n=5)
        
        sources = result['sources']
        summaries = [s['summary'] for s in sources]
        answers = result['responses'][-1]
        
        print(f"✓ 获取到 {len(sources)} 个源")
        print(f"✓ 生成了 {len(answers)} 个答案")
        print()
        
        # 显示第一个答案
        print("初始答案示例:")
        print(answers[0][:300] + "...")
        print()
        
    except Exception as e:
        print(f"✗ 错误: {e}")
        print("\n提示: 确保 Ollama 服务正在运行: ollama serve")
        return
    
    # Step 2: 计算初始印象分数
    print("\nStep 2: 计算初始印象分数...")
    print("-" * 70)
    
    try:
        # 提取引用并计算分数
        init_scores = []
        for answer in answers:
            citations = extract_citations_new(answer)
            score = impression_wordpos_count_simple(citations, n=5)
            init_scores.append(score)
        
        import numpy as np
        avg_init_scores = np.mean(init_scores, axis=0)
        
        print("各源的初始可见度分数:")
        for i, score in enumerate(avg_init_scores):
            print(f"  源 {i+1}: {score:.4f}")
        print()
        
    except Exception as e:
        print(f"✗ 计算分数出错: {e}")
        return
    
    # Step 3: 选择一个源进行优化
    idx_to_optimize = 0  # 优化第一个源
    print(f"\nStep 3: 优化源 {idx_to_optimize + 1}...")
    print("-" * 70)
    
    print(f"原始摘要 (前200字符):")
    print(summaries[idx_to_optimize][:200] + "...")
    print()
    
    # 尝试两种优化方法
    optimization_methods = {
        'authoritative': authoritative_optimization_mine,
        'simple_language': simple_language_mine,
    }
    
    results = {}
    
    for method_name, method_fn in optimization_methods.items():
        print(f"\n应用优化方法: {method_name}")
        try:
            # 优化摘要
            optimized_summary = method_fn(summaries[idx_to_optimize])
            print(f"✓ 优化完成 (前200字符):")
            print(optimized_summary[:200] + "...")
            print()
            
            # 使用优化后的摘要重新生成答案
            print(f"重新生成答案...")
            new_summaries = summaries[:idx_to_optimize] + [optimized_summary] + summaries[idx_to_optimize+1:]
            new_result = get_answer(query, summaries=new_summaries, num_completions=2, n=5)
            new_answers = new_result['responses'][-1]
            
            # 计算新分数
            new_scores = []
            for answer in new_answers:
                citations = extract_citations_new(answer)
                score = impression_wordpos_count_simple(citations, n=5)
                new_scores.append(score)
            
            avg_new_scores = np.mean(new_scores, axis=0)
            
            # 计算改进
            improvement = avg_new_scores[idx_to_optimize] - avg_init_scores[idx_to_optimize]
            improvement_pct = (improvement / avg_init_scores[idx_to_optimize] * 100) if avg_init_scores[idx_to_optimize] > 0 else 0
            
            results[method_name] = {
                'old_score': avg_init_scores[idx_to_optimize],
                'new_score': avg_new_scores[idx_to_optimize],
                'improvement': improvement,
                'improvement_pct': improvement_pct
            }
            
            print(f"✓ 优化效果:")
            print(f"  初始分数: {avg_init_scores[idx_to_optimize]:.4f}")
            print(f"  优化后分数: {avg_new_scores[idx_to_optimize]:.4f}")
            print(f"  改进: {improvement:+.4f} ({improvement_pct:+.2f}%)")
            
        except Exception as e:
            print(f"✗ 优化失败: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Step 4: 总结结果
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    
    if results:
        print(f"\n成功测试 {len(results)} 个优化方法:")
        for method_name, result in results.items():
            print(f"\n{method_name}:")
            print(f"  改进: {result['improvement']:+.4f} ({result['improvement_pct']:+.2f}%)")
            if result['improvement'] > 0:
                print(f"  ✓ 成功提升可见度!")
            else:
                print(f"  ✗ 可见度下降")
    else:
        print("\n未能完成任何优化测试")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    # 可以自定义查询
    test_query = sys.argv[1] if len(sys.argv) > 1 else "What is machine learning?"
    
    print("\n提示: 确保已经:")
    print("  1. 启动 Ollama: ollama serve")
    print("  2. 下载模型: ollama pull gpt-oss")
    print("  3. 配置环境变量 (可选)")
    print()
    input("按回车键开始测试...")
    
    simple_test(test_query)
