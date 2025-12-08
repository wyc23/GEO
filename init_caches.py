#!/usr/bin/env python3
"""
初始化 GEO 项目所需的缓存文件
"""
import os
import json

def init_caches():
    """创建所有必需的缓存文件"""
    
    cache_files = [
        'global_cache.json',
        'gpt-eval-scores-cache_new-new.json',
        'geo_optimizations_cache.json',
        'geo_optimizations_cache_llama3.2.json',
        'geo_optimizations_cache_gpt-3.5-turbo-16k.json',
    ]
    
    print("初始化 GEO 缓存文件...")
    print("=" * 60)
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            print(f"✓ {cache_file} 已存在")
        else:
            with open(cache_file, 'w') as f:
                json.dump({}, f, indent=2)
            print(f"✓ 创建 {cache_file}")
    
    # 创建必要的目录
    dirs = ['response_usages', 'response_usages_16k']
    for dir_name in dirs:
        if os.path.exists(dir_name):
            print(f"✓ 目录 {dir_name}/ 已存在")
        else:
            os.makedirs(dir_name)
            print(f"✓ 创建目录 {dir_name}/")
    
    # 下载必需的 NLTK 数据
    print("\n下载 NLTK 数据包...")
    print("=" * 60)
    try:
        import nltk
        print("下载 punkt...")
        nltk.download('punkt', quiet=True)
        print("✓ punkt 已下载")
        print("下载 punkt_tab...")
        nltk.download('punkt_tab', quiet=True)
        print("✓ punkt_tab 已下载")
    except Exception as e:
        print(f"⚠ NLTK 数据下载失败: {e}")
        print("  可以手动运行: python -c \"import nltk; nltk.download('punkt'); nltk.download('punkt_tab')\"")
    
    print("=" * 60)
    print("✓ 初始化完成!")
    print()

if __name__ == '__main__':
    init_caches()
