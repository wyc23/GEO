#!/usr/bin/env python3
"""
最简化的GEO测试 - 使用预设摘要，不需要搜索引擎
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
from geo_functions import authoritative_optimization_mine
import numpy as np

def minimal_test():
    """
    最简化的测试 - 使用预设的摘要
    """
    print("=" * 70)
    print("GEO 最简化测试 (无需搜索引擎)")
    print("=" * 70)
    
    # 预设的查询和摘要
    query = "What are the benefits of exercise?"
    
    summaries = [
        "Regular exercise improves cardiovascular health, strengthens muscles, and enhances flexibility. It can reduce the risk of chronic diseases like diabetes and heart disease. Exercise also boosts mental health by reducing stress and anxiety.",
        
        "Physical activity helps maintain a healthy weight by burning calories. It improves bone density and reduces the risk of osteoporosis. Exercise also promotes better sleep quality and increases energy levels throughout the day.",
        
        "Working out regularly enhances brain function and memory. It releases endorphins that improve mood and combat depression. Exercise can also strengthen the immune system and increase longevity.",
        
        "Fitness activities improve balance and coordination, reducing fall risk in older adults. They enhance lung capacity and respiratory function. Regular exercise also improves skin health by promoting better blood circulation.",
        
        "Athletic training builds discipline and goal-setting skills. It provides opportunities for social interaction and community building. Exercise can boost self-esteem and confidence through achievement of fitness goals."
    ]
    
    print(f"查询: {query}")
    print(f"使用 {len(summaries)} 个预设摘要")
    print()
    
    # Step 1: 生成初始答案
    print("Step 1: 生成初始答案...")
    print("-" * 70)
    
    try:
        result = get_answer(query, summaries=summaries, num_completions=3, n=5)
        answers = result['responses'][-1]
        
        print(f"✓ 生成了 {len(answers)} 个答案")
        print("\n答案示例:")
        print(answers[0][:400])
        print("...\n")
        
    except Exception as e:
        print(f"✗ 生成答案失败: {e}")
        print("\n可能的原因:")
        print("  1. Ollama 服务未运行 → 执行: ollama serve")
        print("  2. 模型未下载 → 执行: ollama pull gpt-oss")
        print(f"  3. 配置问题 → 检查 OLLAMA_BASE_URL 和 OLLAMA_MODEL")
        return
    
    # Step 2: 计算初始分数
    print("\nStep 2: 计算引用分数...")
    print("-" * 70)
    
    init_scores_list = []
    for i, answer in enumerate(answers):
        citations = extract_citations_new(answer)
        scores = impression_wordpos_count_simple(citations, n=5)
        init_scores_list.append(scores)
        print(f"答案 {i+1} 的源引用分数: {[f'{s:.3f}' for s in scores]}")
    
    avg_init_scores = np.mean(init_scores_list, axis=0)
    print(f"\n平均初始分数: {[f'{s:.3f}' for s in avg_init_scores]}")
    print()
    
    # Step 3: 优化第一个源
    idx_to_optimize = 0
    print(f"\nStep 3: 优化源 {idx_to_optimize + 1}...")
    print("-" * 70)
    print("原始摘要:")
    print(f"  {summaries[idx_to_optimize][:150]}...")
    print()
    
    try:
        print("应用权威性优化...")
        optimized = authoritative_optimization_mine(summaries[idx_to_optimize])
        print("✓ 优化完成")
        print("\n优化后摘要:")
        print(f"  {optimized[:150]}...")
        print()
        
    except Exception as e:
        print(f"✗ 优化失败: {e}")
        return
    
    # Step 4: 用优化后的摘要重新生成答案
    print("\nStep 4: 重新生成答案...")
    print("-" * 70)
    
    new_summaries = [optimized] + summaries[1:]
    
    try:
        new_result = get_answer(query, summaries=new_summaries, num_completions=3, n=5)
        new_answers = new_result['responses'][-1]
        
        print(f"✓ 生成了 {len(new_answers)} 个新答案")
        
    except Exception as e:
        print(f"✗ 重新生成失败: {e}")
        return
    
    # Step 5: 计算新分数和改进
    print("\nStep 5: 计算改进...")
    print("-" * 70)
    
    new_scores_list = []
    for i, answer in enumerate(new_answers):
        citations = extract_citations_new(answer)
        scores = impression_wordpos_count_simple(citations, n=5)
        new_scores_list.append(scores)
        print(f"答案 {i+1} 的源引用分数: {[f'{s:.3f}' for s in scores]}")
    
    avg_new_scores = np.mean(new_scores_list, axis=0)
    print(f"\n平均新分数: {[f'{s:.3f}' for s in avg_new_scores]}")
    
    # 计算改进
    improvement = avg_new_scores[idx_to_optimize] - avg_init_scores[idx_to_optimize]
    if avg_init_scores[idx_to_optimize] > 0:
        improvement_pct = (improvement / avg_init_scores[idx_to_optimize]) * 100
    else:
        improvement_pct = 0
    
    # 结果总结
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)
    print(f"\n目标源 (源 {idx_to_optimize + 1}):")
    print(f"  初始分数:   {avg_init_scores[idx_to_optimize]:.4f}")
    print(f"  优化后分数: {avg_new_scores[idx_to_optimize]:.4f}")
    print(f"  改进:       {improvement:+.4f} ({improvement_pct:+.2f}%)")
    
    if improvement > 0:
        print(f"\n  ✓ 成功! 可见度提升了 {improvement_pct:.2f}%")
    elif improvement < 0:
        print(f"\n  ✗ 可见度下降了 {abs(improvement_pct):.2f}%")
    else:
        print(f"\n  - 可见度无变化")
    
    print("\n所有源的变化:")
    for i in range(5):
        change = avg_new_scores[i] - avg_init_scores[i]
        print(f"  源 {i+1}: {avg_init_scores[i]:.4f} → {avg_new_scores[i]:.4f} ({change:+.4f})")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    print("\n此测试使用预设摘要，不需要搜索引擎")
    print("只需要 Ollama 服务运行即可")
    print("\n准备工作:")
    print("  1. 启动 Ollama: ollama serve")
    print("  2. 确保已下载模型: ollama pull gpt-oss")
    print()
    
    # 检查 Ollama 配置
    import os
    print(f"当前配置:")
    print(f"  OLLAMA_BASE_URL: {os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"  OLLAMA_MODEL: {os.environ.get('OLLAMA_MODEL', 'gpt-oss')}")
    print()
    
    input("按回车键开始测试...")
    
    try:
        minimal_test()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()
