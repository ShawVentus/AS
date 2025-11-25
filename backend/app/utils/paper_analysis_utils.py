import json
from typing import Dict, Any
from app.services.llm_service import llm_service

def analyze_single_paper(paper: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用 LLM 分析单篇论文的相关性。

    Args:
        paper (Dict[str, Any]): 论文元数据字典 (包含 title, abstract, category 等)。
        user_profile (Dict[str, Any]): 用户画像字典。

    Returns:
        Dict[str, Any]: 分析结果字典，包含:
            - why_this_paper (str): 推荐理由
            - relevance_score (float): 相关性评分 (0.0-1.0)
            - accepted (bool): 是否建议接受
            如果解析失败，返回默认的拒绝状态。
    """
    try:
        # 1. 读取 Prompt 模板
        template = llm_service.read_prompt("filter.md")
        
        # 2. 格式化 Prompt
        # 将 user_profile 和 paper 转换为格式化的 JSON 字符串
        profile_str = json.dumps(user_profile, ensure_ascii=False, indent=2)
        paper_str = json.dumps(paper, ensure_ascii=False, indent=2)
        
        prompt = template.format(
            user_profile=profile_str,
            paper=paper_str
        )
        
        # 3. 调用 LLM
        response_str = llm_service.call_llm(prompt)
        
        # 4. 解析结果
        result = json.loads(response_str)
        
        # 确保返回字段存在且类型正确
        return {
            "why_this_paper": result.get("why_this_paper", "No reason provided."),
            "relevance_score": float(result.get("relevance_score", 0.0)),
            "accepted": bool(result.get("accepted", False))
        }
        
    except json.JSONDecodeError:
        print(f"JSON Decode Error for paper {paper.get('id')}: {response_str}")
        return {
            "why_this_paper": "Analysis failed (JSON Error)",
            "relevance_score": 0.0,
            "accepted": False
        }
    except Exception as e:
        print(f"Error analyzing paper {paper.get('id')}: {e}")
        return {
            "why_this_paper": f"Analysis failed ({str(e)})",
            "relevance_score": 0.0,
            "accepted": False
        }
