from typing import List, Dict
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper
import os

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
    
    def get_header(self, report: Report, stats: Dict) -> str:
        """
        生成邮件头部
        
        Args:
            report (Report): 报告对象
            stats (Dict): 统计数据字典
            
        Returns:
            str: 头部 HTML 字符串
        """
        backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        
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
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6; 
                    color: #333; 
                    background: #f5f5f5;
                    margin: 0;
                    padding: 0;
                }}
                .container {{ 
                    max-width: 650px; 
                    margin: 20px auto; 
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 40px 30px;
                    text-align: center;
                }}
                .title {{ 
                    font-size: 26px; 
                    font-weight: bold; 
                    color: white; 
                    margin: 0 0 10px 0;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }}
                .subtitle {{
                    color: rgba(255,255,255,0.9); 
                    font-size: 14px;
                }}
                
                .stats-container {{
                    display: flex;
                    justify-content: space-around;
                    padding: 30px 20px;
                    background: linear-gradient(to bottom, #f8f9fa 0%, white 100%);
                    border-bottom: 1px solid #e9ecef;
                }}
                .stat-card {{
                    text-align: center;
                    flex: 1;
                }}
                .stat-number {{
                    font-size: 36px;
                    font-weight: 700;
                    color: #667eea;
                    margin: 0;
                    line-height: 1;
                }}
                .stat-label {{
                    font-size: 12px;
                    color: #6c757d;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    margin-top: 8px;
                }}
                
                .topics-section {{
                    padding: 20px 30px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #e9ecef;
                }}
                .topics-title {{
                    font-size: 14px;
                    color: #495057;
                    margin-bottom: 10px;
                }}
                .topic-badge {{
                    display: inline-block;
                    background: white;
                    color: #495057;
                    padding: 5px 12px;
                    margin: 4px;
                    border-radius: 20px;
                    font-size: 12px;
                    border: 1px solid #dee2e6;
                }}
                
                .summary-section {{
                    background: linear-gradient(to right, #e3f2fd 0%, #f3e5f5 100%);
                    padding: 25px 30px;
                    margin: 0;
                    border-left: 4px solid #2196f3;
                }}
                .summary-title {{
                    font-weight: 700;
                    color: #1976d2;
                    margin-bottom: 10px;
                    font-size: 16px;
                }}
                .summary-content {{
                    color: #424242;
                    line-height: 1.8;
                }}
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
        arxiv_url = paper.meta.links.get('arxiv') if paper.meta and paper.meta.links else "#"
        
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
                {paper.user_state.why_this_paper if paper.user_state and paper.user_state.why_this_paper else paper.analysis.details.get('tldr', '暂无摘要') if paper.analysis and paper.analysis.details else '暂无摘要'}
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
        
        # 生成论文卡片
        papers_html = '<div style="padding: 30px;">'
        for idx, paper in enumerate(papers[:15], 1):  # 只展示前15篇
            papers_html += self.get_paper_card(idx, paper, report.id)
        papers_html += '</div>'
        
        footer = self.get_footer(report.id, report.user_id)
        
        return header + papers_html + footer
