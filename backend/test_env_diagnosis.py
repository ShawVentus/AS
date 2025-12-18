"""
环境诊断测试
目的：检查 arxivscout 环境中的依赖版本和 API 调用行为
需要在 arxivscout 环境中运行此脚本
"""

import sys
import os

print("="*60)
print("📦 环境信息诊断")
print("="*60)

# 1. 检查 Python 版本
print(f"\nPython 版本: {sys.version}")
print(f"Python 路径: {sys.executable}")

# 2. 检查 OpenAI SDK 版本
try:
    import openai
    print(f"\nOpenAI SDK 版本: {openai.__version__}")
    print(f"OpenAI SDK 路径: {openai.__file__}")
except Exception as e:
    print(f"\n✗ 无法导入 openai: {e}")
    sys.exit(1)

# 3. 检查其他相关包
packages = ['httpx', 'requests', 'pydantic']
for pkg in packages:
    try:
        module = __import__(pkg)
        version = getattr(module, '__version__', '未知')
        print(f"{pkg} 版本: {version}")
    except ImportError:
        print(f"{pkg}: 未安装")

print("\n" + "="*60)
print("🧪 测试 API 调用")
print("="*60)

from openai import OpenAI

BASE_URL = "https://openapi.dp.tech/openapi/v1"
API_KEY = os.getenv("BOHRIUM_API_KEY") or "4c97924ea86e4b40b9cf091dcfd20e44"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 测试 1：基础调用
print("\n[测试 1] 基础调用（无 response_format）")
try:
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": "你好"}],
        temperature=1.2,
    )
    print(f"  ✓ 成功")
    print(f"  返回类型: {type(completion)}")
    print(f"  completion 对象: {type(completion).__name__}")
    print(f"  是否有 choices 属性: {hasattr(completion, 'choices')}")
    if hasattr(completion, 'choices'):
        print(f"  choices[0].message.content: {completion.choices[0].message.content[:50]}...")
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 2：带 response_format
print("\n[测试 2] 带 response_format 参数")
try:
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[{"role": "user", "content": "返回 JSON: {\"test\": \"ok\"}"}],
        temperature=1.2,
        response_format={"type": "json_object"}
    )
    print(f"  ✓ 成功")
    print(f"  返回类型: {type(completion)}")
    print(f"  completion 对象: {type(completion).__name__}")
    print(f"  是否有 choices 属性: {hasattr(completion, 'choices')}")
    if hasattr(completion, 'choices'):
        print(f"  choices[0].message.content: {completion.choices[0].message.content[:50]}...")
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 3：模拟实际代码的调用方式
print("\n[测试 3] 模拟 llm_service.py 的调用方式")
try:
    # 读取 system prompt
    prompt_path = os.path.join(os.path.dirname(__file__), "backend", "app", "prompt", "system.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        print(f"  使用 system prompt: {len(system_prompt)} 字符")
    else:
        system_prompt = "你是一个学术论文分析助手。"
        print(f"  使用默认 system prompt")
    
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "分析这篇论文的主要贡献"},
        ],
        temperature=1.2,
        response_format={"type": "json_object"}
    )
    
    print(f"  ✓ 成功")
    print(f"  返回类型: {type(completion)}")
    print(f"  completion 是字符串吗: {isinstance(completion, str)}")
    
    if isinstance(completion, str):
        print(f"  ⚠️ 警告：API 返回了字符串而非对象！")
        print(f"  字符串内容: {completion[:200]}...")
    else:
        print(f"  ✓ 返回了标准对象")
        response = completion.choices[0].message.content
        print(f"  响应内容: {response[:100]}...")
        
except Exception as e:
    print(f"  ✗ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("💡 诊断结论")
print("="*60)
print("如果测试 1-3 都成功，说明环境本身没问题")
print("如果某个测试失败，说明问题在该测试场景下")
print("如果 completion 是字符串，说明 OpenAI SDK 版本或配置有问题")
print("="*60)
