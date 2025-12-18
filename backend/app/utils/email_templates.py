from typing import List, Dict, Any
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper
import os
import re
from jinja2 import Environment, FileSystemLoader
from premailer import transform
import cssutils
import logging

# 禁止 cssutils 输出不支持现代 CSS 属性的警告日志
cssutils.log.setLevel(logging.CRITICAL)

class EmailTemplates:
    """
    HTML 邮件模板生成器 (Jinja2 版)
    
    主要功能：
    1. 加载 Jinja2 模板
    2. 准备渲染所需的上下文数据
    3. 渲染 HTML 并使用 Premailer 内联 CSS
    """
    
    # 主题标签映射（带 emoji）
    TOPIC_EMOJIS = {
        # 'cs.CV': '🖼️',
        # 'cs.AI': '🤖',
        # 'cs.LG': '🧠',
        # 'cs.CL': '💬',
        # 'cs.RO': '🦾',
        # 'cs.NE': '🌐',
        'default': ''
    }

    def __init__(self):
        """
        初始化模板环境
        """
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def _markdown_to_html(self, text: str) -> str:
        """
        简单的 Markdown 转 HTML 转换器
        
        Args:
            text (str): Markdown 文本
            
        Returns:
            str: HTML 文本
        """
        if not text:
            return ""
            
        # 1. 转义 HTML (简单处理)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # 2. 处理标题 - 统一转换为 h4 以保持样式一致
        # 移除可能存在的 markdown 标记
        text = re.sub(r'^#+ (.*?)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        
        # 3. 处理加粗 **text** -> <strong>text</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # 4. 处理引用 <ref id="xxx"> -> [xxx] (或者链接)
        text = re.sub(r'&lt;ref id="(.*?)"&gt;', r'<a href="https://arxiv.org/abs/\1" style="color: #4f46e5; text-decoration: none;">[\1]</a>', text)
        
        # 5. 处理段落
        paragraphs = text.split('\n\n')
        html_parts = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if not p.startswith('<h'):
                if p.startswith('- '):
                    items = p.split('\n')
                    list_html = '<ul>'
                    for item in items:
                        if item.strip().startswith('- '):
                            list_html += f'<li>{item.strip()[2:]}</li>'
                    list_html += '</ul>'
                    html_parts.append(list_html)
                else:
                    html_parts.append(f'<p>{p.replace(chr(10), "<br>")}</p>')
            else:
                html_parts.append(p)
                
        return '\n'.join(html_parts)

    def _prepare_paper_data(self, index: int, paper: PersonalizedPaper) -> Dict[str, Any]:
        """
        准备单个论文的展示数据
        
        Args:
            index (int): 序号
            paper (PersonalizedPaper): 论文对象
            
        Returns:
            Dict: 模板所需的论文数据字典
        """
        # 获取基础数据
        title = paper.meta.title if paper.meta else "未知标题"
        authors = ', '.join(paper.meta.authors[:3]) + ('...' if len(paper.meta.authors) > 3 else '') if paper.meta and paper.meta.authors else "未知作者"
        published = paper.meta.published_date if paper.meta else "未知日期"
        
        # 处理分类列表
        categories = []
        if paper.meta and paper.meta.category:
            for cat in paper.meta.category:
                emoji = self.TOPIC_EMOJIS.get(cat, self.TOPIC_EMOJIS['default'])
                categories.append({"name": cat, "emoji": emoji})
        else:
            categories.append({"name": "未分类", "emoji": self.TOPIC_EMOJIS['default']})

        relevance = round(paper.user_state.relevance_score, 2) if paper.user_state else 0.0
        arxiv_url = paper.meta.links.arxiv if paper.meta and paper.meta.links else "#"
        
        # 确定徽章颜色
        if relevance >= 0.8:
            badge_color = '#10b981'  # 绿色
        elif relevance >= 0.6:
            badge_color = '#f59e0b'  # 黄色
        else:
            badge_color = '#6b7280'  # 灰色

        # 获取摘要/点评
        tldr = '暂无摘要'
        if paper.user_state and paper.user_state.why_this_paper:
            tldr = paper.user_state.why_this_paper
        elif paper.analysis and paper.analysis.tldr:
            tldr = paper.analysis.tldr

        return {
            "index": index,
            "title": title,
            "link": arxiv_url,
            "authors": authors,
            "published": published,
            "categories": categories,
            "relevance": relevance,
            "badge_color": badge_color,
            "tldr": tldr
        }

    def _process_report_content(self, content: str) -> tuple[str, str | None]:
        """
        处理报告内容：提取摘要并移除冗余标题
        
        Args:
            content (str): 原始 Markdown 内容
            
        Returns:
            tuple[str, str | None]: (清洗后的内容, 提取的摘要文本)
        """
        if not content:
            return "", None
            
        extracted_summary = None
        cleaned_content = content
        
        # 1. 尝试提取 "核心摘要"
        # 匹配 ## 核心摘要 [内容] ## 详细内容 (或结尾)
        summary_match = re.search(r'##\s*核心摘要\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if summary_match:
            extracted_summary = summary_match.group(1).strip()
            # 从内容中移除核心摘要部分
            cleaned_content = cleaned_content.replace(summary_match.group(0), "")
            
        # 2. 移除 "详细内容" 标题及可能的残留字符
        # 移除 "## 详细内容"
        cleaned_content = re.sub(r'##\s*详细内容\s*\n', '', cleaned_content)
        # 移除可能残留的孤立 # 符号 (用户反馈出现的情况)
        cleaned_content = re.sub(r'^\s*#\s*\n', '', cleaned_content, flags=re.MULTILINE)
        
        return cleaned_content.strip(), extracted_summary

    def _markdown_to_html(self, text: str) -> str:
        """
        Markdown 转 HTML 转换器（带自动编号）
        
        Args:
            text (str): Markdown 文本
            
        Returns:
            str: HTML 文本
        """
        if not text:
            return ""
            
        # 1. 转义 HTML
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # 2. 自动编号与标题处理
        # 查找所有标题 (###, ####, #####) 并添加序号
        header_counter = 0
        
        def header_replace(match):
            nonlocal header_counter
            level = len(match.group(1)) # 标题级别 (### = 3)
            title = match.group(2)
            
            # 只对主要的小标题进行编号 (通常是 h3 或 h4)
            # 假设正文中的主要分段是 ### 或 ####
            header_counter += 1
            
            # 映射 Markdown 级别到 HTML 标签
            # 强制统一使用 h4 以保持样式一致
            tag = 'h4'
            
            # 添加序号样式
            numbered_title = f'<span style="background-color: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 8px; vertical-align: middle;">{header_counter}</span>{title}'
            
            return f'<{tag}>{numbered_title}</{tag}>'

        # 匹配 ^(#{3,5}) (内容)
        text = re.sub(r'^(#{3,5})\s+(.*?)$', header_replace, text, flags=re.MULTILINE)
        
        # 处理 ## (如果有剩余的二级标题，转为 h2，不编号)
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        
        # 3. 处理加粗 **text** -> <strong>text</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # 4. 处理引用 <ref id="xxx"> -> [xxx]
        text = re.sub(r'&lt;ref id="(.*?)"&gt;', r'<a href="https://arxiv.org/abs/\1" style="color: #4f46e5; text-decoration: none;">[\1]</a>', text)
        
        # 5. 处理段落和列表
        paragraphs = text.split('\n\n')
        html_parts = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if not p.startswith('<h'):
                if p.startswith('- '):
                    items = p.split('\n')
                    list_html = '<ul>'
                    for item in items:
                        if item.strip().startswith('- '):
                            list_html += f'<li>{item.strip()[2:]}</li>'
                    list_html += '</ul>'
                    html_parts.append(list_html)
                else:
                    html_parts.append(f'<p>{p.replace(chr(10), "<br>")}</p>')
            else:
                html_parts.append(p)
                
        return '\n'.join(html_parts)

    def generate_email_html(self, report: Report, papers: List[PersonalizedPaper], stats: Dict) -> str:
        """
        生成完整邮件 HTML
        
        Args:
            report (Report): 报告对象
            papers (List[PersonalizedPaper]): 论文列表
            stats (Dict): 统计数据
            
        Returns:
            str: 处理后的完整 HTML 内容 (Processed complete HTML content)
        """
        # 1. 准备基础上下文
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        
        # 2. 准备主题列表数据
        category_list = []
        for cat, count in list(stats.get('category_stats', {}).items())[:5]:
            emoji = self.TOPIC_EMOJIS.get(cat, self.TOPIC_EMOJIS['default'])
            category_list.append((cat, count, emoji))
            
        # 3. 准备论文列表数据
        papers_data = []
        for idx, paper in enumerate(papers[:15], 1):
            papers_data.append(self._prepare_paper_data(idx, paper))

        # 4. 处理报告内容
        cleaned_content, extracted_summary = self._process_report_content(report.content)
        
        # 确定最终使用的摘要
        final_summary = extracted_summary if extracted_summary else report.summary

        # 5. 构建完整上下文
        context = {
            "title": report.title,
            "date": report.date,
            "summary": final_summary,
            "content_html": self._markdown_to_html(cleaned_content),
            "stats": {
                "total_papers": stats.get('total_papers', 0),
                "recommended_papers": stats.get('recommended_papers', 0),
                "avg_relevance_score": stats.get('avg_relevance_score', 0.0),
                "category_list": category_list,
                "generated_at": stats.get('generated_at', '') # [NEW] 传递生成时间
            },
            "papers": papers_data,
            "highlight": None,
            "frontend_url": frontend_url,
            "report_id": report.id,
            "user_id": report.user_id,
            "backend_url": os.getenv('BACKEND_URL', 'http://localhost:8000')
        }

        # 6. 渲染模板
        template = self.env.get_template('daily_report.html')
        html_content = template.render(**context)
        
        # 7. 内联 CSS
        final_html = transform(html_content)
        
        return final_html
