"""
玻尔API迁移测试脚本

主要功能：
    1. 验证玻尔API连接是否正常
    2. 验证成本计算逻辑的准确性
    3. 测试多Provider切换功能
    4. 使用真实场景测试论文筛选功能

测试日期：2025-12-16
"""

import os
import sys
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.services.llm_service import llm_service

def test_bohrium_connection():
    """
    测试1：验证玻尔API连接
    
    功能说明：
        发送简单的测试请求到玻尔API，检查响应是否正常。
        验证token统计和成本计算是否正确返回。
    """
    print("=" * 60)
    print("测试1：玻尔API连接测试")
    print("=" * 60)
    
    # 确保使用bohrium provider
    original_provider = settings.LLM_PROVIDER
    os.environ["LLM_PROVIDER"] = "bohrium"
    settings.LLM_PROVIDER = "bohrium"
    
    try:
        # 重新初始化服务
        from app.services.llm_service import QwenService
        test_service = QwenService()
        
        # 简单的测试prompt
        test_prompt = "请用一句话介绍你自己。"
        
        response, usage = test_service.call_llm(
            test_prompt, 
            model="qwen-plus",
            response_format=None
        )
        
        print(f"✅ 请求成功")
        print(f"📊 响应内容: {response[:100]}...")
        print(f"📈 Token统计:")
        print(f"   - 输入tokens: {usage.get('prompt_tokens', 0)}")
        print(f"   - 输出tokens: {usage.get('completion_tokens', 0)}")
        print(f"   - 总tokens: {usage.get('total_tokens', 0)}")
        print(f"   - 缓存命中tokens: {usage.get('cache_hit_tokens', 0)}")
        print(f"   - 成本: ${usage.get('cost', 0):.6f}")
        print(f"   - 模型: {usage.get('model', 'N/A')}")
        
        # 验证必要字段
        assert usage.get('prompt_tokens', 0) > 0, "prompt_tokens应该大于0"
        assert usage.get('completion_tokens', 0) > 0, "completion_tokens应该大于0"
        assert usage.get('cost', 0) > 0, "成本应该已计算"
        
        print("✅ 所有验证通过")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始配置
        os.environ["LLM_PROVIDER"] = original_provider
        settings.LLM_PROVIDER = original_provider

def test_cost_calculation():
    """
    测试2：验证成本计算准确性
    
    功能说明：
        使用已知token数量的请求，验证自动成本计算公式是否正确。
        对比手动计算和自动计算的成本，确保误差在可接受范围内。
    """
    print("\n" + "=" * 60)
    print("测试2：成本计算准确性验证")
    print("=" * 60)
    
    os.environ["LLM_PROVIDER"] = "bohrium"
    settings.LLM_PROVIDER = "bohrium"
    
    try:
        from app.services.llm_service import QwenService
        test_service = QwenService()
        
        # 使用固定内容的prompt
        test_prompt = "1+1等于几？请只回答数字。"
        
        response, usage = test_service.call_llm(
            test_prompt,
            model="qwen-plus",
            response_format=None
        )
        
        # 获取定价
        pricing = settings.get_model_pricing("qwen-plus")
        
        # 手动计算成本
        manual_input_cost = (usage['prompt_tokens'] / 1_000_000) * pricing['input_price']
        manual_output_cost = (usage['completion_tokens'] / 1_000_000) * pricing['output_price']
        manual_total_cost = manual_input_cost + manual_output_cost
        
        # 自动计算的成本
        auto_cost = usage.get('cost', 0)
        
        print(f"📊 Token统计:")
        print(f"   - 输入: {usage['prompt_tokens']} tokens")
        print(f"   - 输出: {usage['completion_tokens']} tokens")
        print(f"\n💰 成本计算:")
        print(f"   - 输入价格: ${pricing['input_price']}/1M tokens")
        print(f"   - 输出价格: ${pricing['output_price']}/1M tokens")
        print(f"   - 手动计算: ${manual_total_cost:.8f}")
        print(f"   - 自动计算: ${auto_cost:.8f}")
        print(f"   - 差异: ${abs(manual_total_cost - auto_cost):.8f}")
        
        # 允许微小的浮点误差
        assert abs(manual_total_cost - auto_cost) < 0.000001, "成本计算差异过大"
        
        print("✅ 成本计算准确")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_provider_switching():
    """
    测试3：验证多Provider切换功能
    
    功能说明：
        测试在bohrium、openrouter、dashscope之间切换。
        验证每个已配置API Key的Provider都能正常工作。
    """
    print("\n" + "=" * 60)
    print("测试3：多Provider切换功能")
    print("=" * 60)
    
    providers = ["bohrium", "openrouter", "dashscope"]
    results = {}
    
    for provider in providers:
        print(f"\n🔄 测试Provider: {provider}")
        
        # 检查是否配置了API key
        os.environ["LLM_PROVIDER"] = provider
        settings.LLM_PROVIDER = provider
        
        try:
            config = settings.get_llm_config()
            if not config["api_key"]:
                print(f"⚠️  {provider} 未配置API Key，跳过")
                results[provider] = "未配置"
                continue
                
            from app.services.llm_service import QwenService
            test_service = QwenService()
            
            response, usage = test_service.call_llm(
                "你好",
                model="qwen-plus",
                response_format=None
            )
            
            print(f"✅ {provider} 工作正常")
            print(f"   - Tokens: {usage.get('total_tokens', 0)}")
            print(f"   - 成本: ${usage.get('cost', 0):.6f}")
            results[provider] = "成功"
            
        except Exception as e:
            print(f"❌ {provider} 失败: {e}")
            results[provider] = f"失败: {str(e)[:50]}"
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for provider, status in results.items():
        print(f"  {provider}: {status}")

def test_paper_filter():
    """
    测试4：实际workflow测试 - 论文筛选
    
    功能说明：
        使用真实的论文数据测试filter_paper功能。
        验证成本统计是否正确记录在返回结果中。
    """
    print("\n" + "=" * 60)
    print("测试4：论文筛选功能（实际场景）")
    print("=" * 60)
    
    os.environ["LLM_PROVIDER"] = "bohrium"
    settings.LLM_PROVIDER = "bohrium"
    
    try:
        from app.services.llm_service import QwenService
        test_service = QwenService()
        
        # 模拟论文数据
        test_paper = {
            "title": "Attention Is All You Need",
            "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
            "category": "cs.CL"
        }
        
        test_profile = "研究自然语言处理和深度学习，特别关注Transformer架构"
        
        result = test_service.filter_paper(test_paper, test_profile)
        
        print(f"✅ 筛选完成")
        print(f"📊 结果:")
        print(f"   - 相关性: {result.get('is_relevant', False)}")
        print(f"   - 评分: {result.get('score', 0)}/10")
        print(f"   - 理由: {result.get('reason', 'N/A')[:100]}...")
        print(f"💰 成本统计:")
        usage = result.get('_usage', {})
        print(f"   - 输入tokens: {usage.get('prompt_tokens', 0)}")
        print(f"   - 输出tokens: {usage.get('completion_tokens', 0)}")
        print(f"   - 成本: ${usage.get('cost', 0):.6f}")
        
        assert '_usage' in result, "结果应包含_usage字段"
        assert usage.get('cost', 0) > 0, "成本应已计算"
        
        print("✅ 测试通过")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 开始玻尔API迁移测试\n")
    
    # 保存原始配置
    original_provider = settings.LLM_PROVIDER
    
    try:
        # 运行所有测试
        test_bohrium_connection()
        test_cost_calculation()
        test_provider_switching()
        test_paper_filter()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    finally:
        # 恢复原始配置
        os.environ["LLM_PROVIDER"] = original_provider
        settings.LLM_PROVIDER = original_provider
