from typing import List, Dict
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper
import os
import re

class EmailTemplates:
    """
    HTML 邮件模板生成器
    
    主要功能：
    1. 生成包含统计数据的邮件头部
    2. 生成精美的论文展示卡片
    3. 生成包含反馈链接的底部
    4. 组合生成完整的 HTML 邮件内容
    """
    
    # 主题标签映射（带 emoji）
    TOPIC_EMOJIS = {
        'cs.CV': '🖼️',
        'cs.AI': '🤖',
        'cs.LG': '🧠',
        'cs.CL': '💬',
        'cs.RO': '🦾',
        'cs.NE': '🌐',
        'default': '📄'
    }
    # ... (existing code) ...

    def get_header(self, report: Report, stats: Dict) -> str:
        # ... (existing code) ...
        # Add CSS for report content
        # Insert before </style>
        # 主题统计
        category_badges = ""
        for cat, count in list(stats.get('category_stats', {}).items())[:5]:
            emoji = self.TOPIC_EMOJIS.get(cat, self.TOPIC_EMOJIS['default'])
            category_badges += f'<span class="topic-badge">{emoji} {cat} ({count})</span>'
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                /* ... (existing styles) ... */
                
                .report-content {{
                    padding: 30px;
                    background: white;
                    border-bottom: 1px solid #e9ecef;
                    color: #2d3748;
                }}
                .report-content h3 {{
                    font-size: 18px;
                    color: #2c5282;
                    margin-top: 25px;
                    margin-bottom: 15px;
                    border-left: 4px solid #4299e1;
                    padding-left: 10px;
                }}
                .report-content h4 {{
                    font-size: 16px;
                    color: #4a5568;
                    margin-top: 20px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }}
                .report-content p {{
                    margin-bottom: 15px;
                    line-height: 1.7;
                    text-align: justify;
                }}
                .report-content strong {{
                    color: #2b6cb0;
                }}
                .report-content ul {{
                    padding-left: 20px;
                    margin-bottom: 15px;
                }}
                .report-content li {{
                    margin-bottom: 8px;
                }}
                
                /* ... (rest of styles) ... */
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 class="title">📊 {report.title}</h1>
                    <div class="subtitle">玻尔平台 • {report.date}</div>
                </div>
                
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-number">{stats['total_papers']}</div>
                        <div class="stat-label">📄 爬取论文</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats['recommended_papers']}</div>
                        <div class="stat-label">⭐ 推荐论文</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{stats['avg_relevance_score']}</div>
                        <div class="stat-label">📈 平均相关度</div>
                    </div>
                </div>
                
                <div class="topics-section">
                    <div class="topics-title">🏷️ 主题分布</div>
                    {category_badges}
                </div>
                
                <div class="summary-section">
                    <div class="summary-title">核心摘要</div>
                    <div class="summary-content">{report.summary}</div>
                </div>
        '''

    def get_paper_card(self, index: int, paper: PersonalizedPaper, report_id: str) -> str:
        """
        生成论文卡片
        
        Args:
            index (int): 序号
            paper (PersonalizedPaper): 论文对象
            report_id (str): 报告ID
            
        Returns:
            str: 论文卡片 HTML
        """
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        
        # 获取数据
        title = paper.meta.title if paper.meta else "未知标题"
        authors = ', '.join(paper.meta.authors[:3]) + ('...' if len(paper.meta.authors) > 3 else '') if paper.meta and paper.meta.authors else "未知作者"
        published = paper.meta.published_date if paper.meta else "未知日期"
        category = paper.meta.category[0] if paper.meta and paper.meta.category else "未分类"
        relevance = round(paper.user_state.relevance_score, 2) if paper.user_state else 0.0
        arxiv_url = paper.meta.links.arxiv if paper.meta and paper.meta.links else "#"
        
        # 相关性徽章颜色
        if relevance >= 0.8:
            badge_color = '#28a745'  # 绿色
        elif relevance >= 0.6:
            badge_color = '#ffc107'  # 黄色
        else:
            badge_color = '#6c757d'  # 灰色
        
        return f'''
        <div style="background: white; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; margin-bottom: 20px; transition: all 0.3s;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 18px; color: #212529; flex: 1;">
                    <a href="{arxiv_url}" style="color: #667eea; text-decoration: none;">{index}. {title}</a>
                </h3>
                <span style="background: {badge_color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; white-space: nowrap; margin-left: 10px;">
                    {relevance}
                </span>
            </div>
            
            <div style="font-size: 13px; color: #6c757d; margin-bottom: 10px;">
                <span>👤 {authors}</span> • 
                <span>📅 {published}</span> • 
                <span style="background: #e9ecef; padding: 2px 8px; border-radius: 4px;">{self.TOPIC_EMOJIS.get(category, self.TOPIC_EMOJIS['default'])} {category}</span>
            </div>
            
            <div style="font-size: 14px; color: #495057; line-height: 1.6; margin-bottom: 15px;">
                {paper.user_state.why_this_paper if paper.user_state and paper.user_state.why_this_paper else paper.analysis.tldr if paper.analysis and paper.analysis.tldr else '暂无摘要'}
            </div>
            
            <a href="{arxiv_url}" style="display: inline-block; background: #667eea; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-size: 13px;">
                查看原文 →
            </a>
        </div>
        '''
    
    def get_footer(self, report_id: str, user_id: str) -> str:
        """
        生成邮件底部
        
        Args:
            report_id (str): 报告ID
            user_id (str): 用户ID
            
        Returns:
            str: 底部 HTML
        """
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        track_pixel_url = f"{backend_url}/api/v1/email/track/{report_id}/{user_id}"
        
        return f'''
                <div style="background: #f8f9fa; padding: 30px 30px 20px; text-align: center; border-top: 1px solid #e9ecef;">
                    <div style="font-size: 16px; color: #495057; margin-bottom: 20px; font-weight: 600;">
                        今天的报告如何？
                    </div>
                    <div style="display: flex; justify-content: center; gap: 15px; margin-bottom: 20px;">
                        <a href="{frontend_url}/feedback?report={report_id}&rating=1" style="font-size: 32px; text-decoration: none; transition: transform 0.2s;">⭐</a>
                        <a href="{frontend_url}/feedback?report={report_id}&rating=2" style="font-size: 32px; text-decoration: none; transition: transform 0.2s;">⭐⭐</a>
                        <a href="{frontend_url}/feedback?report={report_id}&rating=3" style="font-size: 32px; text-decoration: none; transition: transform 0.2s;">⭐⭐⭐</a>
                        <a href="{frontend_url}/feedback?report={report_id}&rating=4" style="font-size: 32px; text-decoration: none; transition: transform 0.2s;">⭐⭐⭐⭐</a>
                        <a href="{frontend_url}/feedback?report={report_id}&rating=5" style="font-size: 32px; text-decoration: none; transition: transform 0.2s;">⭐⭐⭐⭐⭐</a>
                    </div>
                    <a href="{frontend_url}/reports/{report_id}" style="display: inline-block; background: #667eea; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-bottom: 20px;">
                        查看完整报告 →
                    </a>
                </div>
                
                <div style="background: #212529; color: #adb5bd; padding: 20px; text-align: center;">
                    <p style="margin: 0 0 10px 0; font-size: 13px;">由玻尔平台生成</p>
                    <p style="margin: 0; font-size: 12px;">
                        <a href="{frontend_url}/settings" style="color: #667eea; text-decoration: none;">邮件设置</a>
                    </p>
                </div>
            </div>
            
            <!-- 追踪像素 -->
            <img src="{track_pixel_url}" width="1" height="1" style="display:none;" />
        </body>
        </html>
        '''
    def _markdown_to_html(self, text: str) -> str:
        """
        简单的 Markdown 转 HTML 转换器
        """
        if not text:
            return ""
            
        # 1. 转义 HTML (简单处理)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # 2. 处理标题
        # ### Title -> <h3>Title</h3>
        text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        # #### Title -> <h4>Title</h4>
        text = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        # ## Title -> <h2>Title</h2>
        text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        
        # 3. 处理加粗 **text** -> <strong>text</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # 4. 处理引用 <ref id="xxx"> -> [xxx] (或者链接)
        # 假设格式是 <ref id="2512.08185">
        # 转换为链接到 Arxiv
        text = re.sub(r'&lt;ref id="(.*?)"&gt;', r'<a href="https://arxiv.org/abs/\1" style="color: #667eea; text-decoration: none;">[\1]</a>', text)
        
        # 5. 处理段落
        # 将双换行视为段落分隔
        paragraphs = text.split('\n\n')
        html_parts = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # 如果不是标题开头，包裹 <p>
            if not p.startswith('<h'):
                # 处理列表
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

    def get_content_section(self, report: Report) -> str:
        """
        生成报告正文部分
        """
        if not report.content:
            return ""
            
        html_content = self._markdown_to_html(report.content)
        
        return f'''
        <div class="report-content">
            {html_content}
        </div>
        '''

    def generate_email_html(self, report: Report, papers: List[PersonalizedPaper], stats: Dict) -> str:
        """
        生成完整邮件 HTML
        
        Args:
            report (Report): 报告对象
            papers (List[PersonalizedPaper]): 论文列表
            stats (Dict): 统计数据
            
        Returns:
            str: 完整 HTML 内容
        """
        header = self.get_header(report, stats)
        
        # 生成正文内容
        content_html = self.get_content_section(report)
        
        # 生成论文卡片
        papers_html = '<div style="padding: 30px; background: #f8f9fa;">'
        papers_html += '<div style="font-size: 16px; font-weight: bold; color: #2d3748; margin-bottom: 20px; padding-left: 10px; border-left: 4px solid #667eea;">推荐论文列表</div>'
        for idx, paper in enumerate(papers[:15], 1):  # 只展示前15篇
            papers_html += self.get_paper_card(idx, paper, report.id)
        papers_html += '</div>'
        
        footer = self.get_footer(report.id, report.user_id)
        
        return header + content_html + papers_html + footer
