from typing import List, Dict, Tuple
from datetime import datetime
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper

class EmailFormatter:
    """
    邮件格式化器
    
    主要功能：
    1. 计算论文统计数据（总数、推荐数、分类分布、平均相关度）
    2. 调用模板引擎生成 HTML 邮件内容
    3. 生成纯文本备选邮件内容
    """
    
    def get_statistics(self, papers: List[PersonalizedPaper]) -> Dict[str, any]:
        """
        计算统计数据
        
        Args:
            papers (List[PersonalizedPaper]): 论文列表
            
        Returns:
            Dict[str, any]: 统计数据字典
        """
        total = len(papers)
        recommended = sum(1 for p in papers if (p.user_state and p.user_state.relevance_score >= 0.7))
        
        # 统计分类
        category_stats = {}
        for paper in papers:
            if paper.meta and paper.meta.category:
                for cat in paper.meta.category:
                    category_stats[cat] = category_stats.get(cat, 0) + 1
        
        # 平均相关性
        scores = [p.user_state.relevance_score for p in papers if p.user_state and p.user_state.relevance_score]
        avg_relevance = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'total_papers': total,
            'recommended_papers': recommended,
            'category_stats': category_stats,
            'avg_relevance_score': round(avg_relevance, 2),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    def format_report_to_html(self, report: Report, papers: List[PersonalizedPaper]) -> Tuple[str, str, Dict]:
        """
        将报告格式化为 HTML 邮件
        
        Args:
            report (Report): 报告对象
            papers (List[PersonalizedPaper]): 论文列表
            
        Returns:
            Tuple[str, str, Dict]: (HTML内容, 纯文本内容, 统计数据)
        """
        from app.utils.email_templates import EmailTemplates
        
        # 计算统计
        stats = self.get_statistics(papers)
        
        # 生成 HTML
        templates = EmailTemplates()
        html = templates.generate_email_html(
            report=report,
            papers=papers,
            stats=stats
        )
        
        # 生成纯文本备选
        plain = self.generate_plain_text(report, papers, stats)
        
        return html, plain, stats
    
    def generate_plain_text(self, report: Report, papers: List[PersonalizedPaper], stats: Dict) -> str:
        """
        生成纯文本邮件（备选方案）
        
        Args:
            report (Report): 报告对象
            papers (List[PersonalizedPaper]): 论文列表
            stats (Dict): 统计数据
            
        Returns:
            str: 纯文本内容
        """
        import os
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        
        lines = [
            f"【玻尔平台论文日报】{report.date}",
            "",
            f"报告标题：{report.title}",
            "",
            "=" * 50,
            f"📊 统计数据",
            f"  • 爬取论文：{stats['total_papers']} 篇",
            f"  • 推荐论文：{stats['recommended_papers']} 篇",
            f"  • 平均相关度：{stats['avg_relevance_score']}",
            "",
            "=" * 50,
            f"核心摘要：",
            report.summary,
            "",
            "=" * 50,
            "推荐论文列表：",
            ""
        ]
        
        for idx, paper in enumerate(papers[:10], 1):  # 只展示前10篇
            lines.extend([
                f"{idx}. {paper.meta.title}",
                f"   作者：{', '.join(paper.meta.authors[:3])}{'...' if len(paper.meta.authors) > 3 else ''}",
                f"   相关性：{paper.user_state.relevance_score if paper.user_state else 'N/A'}",
                f"   链接：{paper.meta.links.get('arxiv') if paper.meta.links else 'N/A'}",
                ""
            ])
        
        lines.extend([
            "=" * 50,
            f"查看完整报告：{frontend_url}/reports/{report.id}",
            ""
        ])
        
        return "\n".join(lines)
