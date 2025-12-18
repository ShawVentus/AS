"""
测试玻尔 API 是否支持 response_format 参数
目的：验证 response_format={"type": "json_object"} 是否导致 API 调用失败
"""

import os
from openai import OpenAI

# 玻尔 API 配置
BASE_URL = "https://openapi.dp.tech/openapi/v1"
API_KEY = os.getenv("ACCESS_KEY") or "4c97924ea86e4b40b9cf091dcfd20e44"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def test_without_response_format():
    """测试 1：不带 response_format 参数（基准测试）"""
    print("\n" + "="*60)
    print("测试 1：不带 response_format 参数")
    print("="*60)
    
    try:
        resp = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "user", "content": "请以 JSON 格式返回：{\"name\": \"张三\", \"age\": 25}"}
            ],
            temperature=1.2,
        )
        
        print("✓ 调用成功")
        print(f"  返回类型: {type(resp)}")
        print(f"  返回内容: {resp.choices[0].message.content}")
        print(f"  Token 使用: {resp.usage.total_tokens}")
        return True
        
    except Exception as e:
        print(f"✗ 调用失败")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")
        return False


def test_with_json_object_format():
    """测试 2：带 response_format={"type": "json_object"} 参数"""
    print("\n" + "="*60)
    print("测试 2：带 response_format={'type': 'json_object'} 参数")
    print("="*60)
    
    try:
        resp = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "user", "content": "请以 JSON 格式返回：{\"name\": \"张三\", \"age\": 25}"}
            ],
            temperature=1.2,
            response_format={"type": "json_object"}  # 关键参数
        )
        
        print("✓ 调用成功")
        print(f"  返回类型: {type(resp)}")
        print(f"  返回内容: {resp.choices[0].message.content}")
        print(f"  Token 使用: {resp.usage.total_tokens}")
        return True
        
    except Exception as e:
        print(f"✗ 调用失败")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")
        
        # 打印详细的错误堆栈
        import traceback
        print(f"\n  详细堆栈:")
        print("  " + "\n  ".join(traceback.format_exc().split("\n")))
        return False


def test_with_text_format():
    """测试 3：带 response_format={"type": "text"} 参数"""
    print("\n" + "="*60)
    print("测试 3：带 response_format={'type': 'text'} 参数")
    print("="*60)
    
    try:
        resp = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "user", "content": "请随便说一句话"}
            ],
            temperature=1.2,
            response_format={"type": "text"}  # 尝试 text 类型
        )
        
        print("✓ 调用成功")
        print(f"  返回类型: {type(resp)}")
        print(f"  返回内容: {resp.choices[0].message.content}")
        print(f"  Token 使用: {resp.usage.total_tokens}")
        return True
        
    except Exception as e:
        print(f"✗ 调用失败")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "🔬 开始测试玻尔 API 的 response_format 参数支持情况")
    print("模型: qwen-plus")
    print("Base URL: https://openapi.dp.tech/openapi/v1")
    
    results = {}
    
    # 执行三个测试
    results["无 response_format"] = test_without_response_format()
    results["json_object 格式"] = test_with_json_object_format()
    results["text 格式"] = test_with_text_format()
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {test_name:20s}: {status}")
    
    # 结论
    print("\n" + "="*60)
    print("💡 结论")
    print("="*60)
    
    if results["无 response_format"] and not results["json_object 格式"]:
        print("  玻尔 API 【不支持】 response_format={'type': 'json_object'} 参数")
        print("  建议：在调用玻尔 API 时，不要传递 response_format 参数")
    elif results["无 response_format"] and results["json_object 格式"]:
        print("  玻尔 API 【支持】 response_format={'type': 'json_object'} 参数")
        print("  说明：问题可能不在于 response_format 参数")
    else:
        print("  基础调用失败，请检查 API Key 和网络连接")
    
    print("="*60 + "\n")
