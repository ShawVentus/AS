import json
from typing import Dict, Any
from app.services.llm_service import llm_service

def filter_single_paper(paper_str: str, user_profile_str: str) -> Dict[str, Any]:
    """
    使用 LLM 筛选单篇论文的相关性 (Personalized Filter)。

    Args:
        paper_str (str): 序列化后的论文元数据字符串。
        user_profile_str (str): 序列化后的用户画像字符串。

    Returns:
        Dict[str, Any]: 筛选结果字典 (对应 PaperFilter 模型):
            - why_this_paper (str)
            - relevance_score (float)
            - accepted (bool)
    """
    try:
        # 1. 读取 Prompt 模板
        template = llm_service.read_prompt("filter.md")
        
        # 2. 格式化 Prompt
        prompt = template.format(
            user_profile=user_profile_str,
            paper=paper_str
        )
        
        # 3. 调用 LLM
        response_str = llm_service.call_llm(prompt)
        
        # 4. 解析结果
        result = json.loads(response_str)
        
        return {
            "why_this_paper": result.get("why_this_paper", "No reason provided."),
            "relevance_score": float(result.get("relevance_score", 0.0)),
            "accepted": bool(result.get("accepted", False))
        }
        
    except Exception as e:
        print(f"Error filtering paper {paper.get('id')}: {e}")
        return {
            "why_this_paper": f"Filter failed ({str(e)})",
            "relevance_score": 0.0,
            "accepted": False
        }

def analyze_paper_content(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用 LLM 分析单篇论文的内容 (Public Analysis)。

    Args:
        paper (Dict[str, Any]): 论文元数据字典 (需包含 abstract, comment)。

    Returns:
        Dict[str, Any]: 分析结果字典 (对应 PaperAnalysis 模型)。
    """
    try:
        # 1. 读取 Prompt 模板
        template = llm_service.read_prompt("analyze.md")
        
        # 2. 格式化 Prompt
        # 确保 comment 不为 None
        comment = paper.get("comment") or ""
        
        prompt = template.format(
            abstract=paper.get("abstract", ""),
            comment=comment
        )
        
        # 3. 调用 LLM
        response_str = llm_service.call_llm(prompt)
        
        # 4. 解析结果
        return json.loads(response_str)
        
    except Exception as e:
        print(f"Error analyzing paper content {paper.get('id')}: {e}")
        return {}
