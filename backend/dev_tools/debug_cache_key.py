#!/usr/bin/env python3
"""调试缓存键生成工具"""
import hashlib
import sys


def normalize_text(text: str) -> str:
    """归一化文本（和cache_service.py中相同的逻辑）"""
    value = (text or "").strip().lower()
    for char in ["\n", "\r", "\t", "，", "。", "？", "！", "、", ",", ".", "?", "!", "；", ";", ":", "："]:
        value = value.replace(char, " ")
    value = " ".join(value.split())

    synonym_map = {
        "多少钱": "价格",
        "收费标准": "价格",
        "价位": "价格",
        "对比一下": "比较",
        "比较下": "比较",
    }
    for src, dst in synonym_map.items():
        value = value.replace(src, dst)
    return value


def short_hash(text: str) -> str:
    """生成短哈希"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:20]


def build_context_signature(messages: list[str]) -> str:
    """构建上下文签名"""
    pairs = [f"user:{msg[:220]}" for msg in messages[-6:]]
    return "\n".join(pairs)


def build_cache_key(owner_key: str, query: str, context_messages: list[str]) -> dict:
    """构建缓存键"""
    normalized_query = normalize_text(query)
    context_sig = build_context_signature(context_messages)
    context_hash = short_hash(context_sig)
    query_hash = short_hash(normalized_query)
    
    model = "qwen:qwen3.5-122b-a10b:chat-v1"
    
    private_key = f"chat:v1:private:{owner_key}:{model}:{query_hash}:{context_hash}"
    public_key = f"chat:v1:public:*:{model}:{query_hash}:{context_hash}"
    
    return {
        "原始问题": query,
        "归一化问题": normalized_query,
        "问题哈希": query_hash,
        "上下文签名": context_sig,
        "上下文哈希": context_hash,
        "私有缓存键": private_key,
        "公共缓存键": public_key,
    }


if __name__ == "__main__":
    print("=" * 80)
    print("缓存键调试工具")
    print("=" * 80)
    
    # 用户A：第一条消息（新对话）
    print("\n【用户A - 新对话】")
    query_A = "想要投资新能源，你有什么建议"
    context_A = [query_A]  # 第一条消息，历史只有自己
    
    result_A = build_cache_key("user_A", query_A, context_A)
    for key, value in result_A.items():
        if "缓存键" in key:
            print(f"{key}:")
            print(f"  {value}")
        else:
            print(f"{key}: {value}")
    
    # 用户B：第一条消息（新对话）
    print("\n" + "-" * 80)
    print("\n【用户B - 新对话（相同问题）】")
    query_B = "想要投资新能源，你有什么建议"
    context_B = [query_B]  # 第一条消息
    
    result_B = build_cache_key("user_B", query_B, context_B)
    for key, value in result_B.items():
        if "缓存键" in key:
            print(f"{key}:")
            print(f"  {value}")
        else:
            print(f"{key}: {value}")
    
    # 比较
    print("\n" + "=" * 80)
    print("【比对结果】")
    print(f"公共缓存键是否相同: {result_A['公共缓存键'] == result_B['公共缓存键']}")
    print(f"私有缓存键是否相同: {result_A['私有缓存键'] == result_B['私有缓存键']}")
    
    # 用户C：有历史对话
    print("\n" + "=" * 80)
    print("\n【用户C - 有历史对话（相同问题）】")
    query_C = "想要投资新能源，你有什么建议"
    context_C = [
        "美国股市怎么样",
        query_C
    ]
    
    result_C = build_cache_key("user_C", query_C, context_C)
    for key, value in result_C.items():
        if "缓存键" in key:
            print(f"{key}:")
            print(f"  {value}")
        else:
            print(f"{key}: {value}")
    
    print("\n" + "=" * 80)
    print("【比对结果 - A vs C】")
    print(f"公共缓存键是否相同: {result_A['公共缓存键'] == result_C['公共缓存键']}")
    print(f"原因: {'相同' if result_A['上下文哈希'] == result_C['上下文哈希'] else '上下文不同'}")
    
    # 自定义测试
    if len(sys.argv) > 1:
        print("\n" + "=" * 80)
        print("\n【自定义测试】")
        custom_query = " ".join(sys.argv[1:])
        custom_result = build_cache_key("custom_user", custom_query, [custom_query])
        for key, value in custom_result.items():
            if "缓存键" in key:
                print(f"{key}:")
                print(f"  {value}")
            else:
                print(f"{key}: {value}")
    
    print("\n" + "=" * 80)
