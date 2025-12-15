from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
import uuid
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper
from app.schemas.user import UserProfile
from app.services.llm_service import llm_service
from app.utils.email_sender import email_sender
from app.utils.email_formatter import EmailFormatter
from app.core.database import get_db

class ReportService:
    """
    报告服务类
    
    主要功能：
    1. 生成每日报告（调用 LLM）
    2. 计算报告统计数据
    3. 发送格式化的 HTML 邮件
    4. 处理用户反馈
    5. 记录系统日志和邮件追踪事件
    """
    
    def __init__(self):
        self.db = get_db()

    def get_reports(self) -> List[Report]:
        """
        从数据库获取所有生成的报告。

        Returns:
            List[Report]: 报告对象列表，按日期倒序排列。
        """
        try:
            response = self.db.table("reports").select("*").order("date", desc=True).execute()
            if response.data:
                return [Report(**r) for r in response.data]
            return []
        except Exception as e:
            print(f"Error fetching reports: {e}")
            return []

    def generate_daily_report(self, papers: List[PersonalizedPaper], user_profile: UserProfile) -> tuple[Report, Dict[str, int]]:
        """
        生成每日报告并自动发送邮件。

        Args:
            papers (List[PersonalizedPaper]): 用于生成报告的论文列表。
            user_profile (UserProfile): 用户画像，用于定制报告内容。

        Returns:
            Report: 生成的报告对象。
        """
        # 1. 准备数据供 LLM 使用
        papers_data = []
        for p in papers:
            flat_p = p.meta.model_dump()
            if p.analysis:
                flat_p.update(p.analysis.model_dump())
            if p.user_state:
                flat_p.update(p.user_state.model_dump())
            papers_data.append(flat_p)
        
        # 2. 调用 LLM 生成报告
        profile_str = json.dumps(user_profile.model_dump(), ensure_ascii=False, indent=2)
        llm_result = llm_service.generate_report(papers_data, profile_str)
        print(f"DEBUG: LLM Report Result: {json.dumps(llm_result, ensure_ascii=False, indent=2)}")
        
        # LLM 失败时的退路
        if not llm_result or not llm_result.get("title"):
            print("❌ Report generation failed. Sending alert email...")
            try:
                alert_subject = "【系统报警】日报生成失败"
                alert_content = f"用户 {user_profile.info.name} ({user_profile.info.id}) 的日报生成失败，请检查后台日志。"
                email_sender.send_email("2962326813@qq.com", alert_subject, f"<p>{alert_content}</p>", alert_content)
            except Exception as e:
                print(f"Failed to send alert email: {e}")

            llm_result = {
                "title": f"{datetime.now().strftime('%Y/%m/%d')} - Daily Report (Fallback)",
                "summary": "Failed to generate report via LLM.",
                "content": "No content generated.",
                "ref_papers": []
            }
            
        # 3. 计算统计数据
        total_count = len(papers)
        recommended_count = sum(1 for p in papers if (p.user_state and p.user_state.relevance_score >= 0.7))
        
        # 4. 创建 Report 对象
        report = Report(
            id=str(uuid.uuid4()),
            user_id=user_profile.info.id,
            email=user_profile.info.email,  # [Add] 填充 email 字段
            title=llm_result.get("title", "Daily Report"),
            date=datetime.now().strftime("%Y-%m-%d"),
            summary=llm_result.get("summary", ""),
            content=llm_result.get("content", ""),
            ref_papers=llm_result.get("ref_papers", []),
            total_papers_count=total_count,
            recommended_papers_count=recommended_count
        )
        
        # 5. 保存到数据库
        try:
            # [Fix] 使用 by_alias=False 确保使用 Python 属性名 (ref_papers) 而不是别名 (refPapers)
            # 假设数据库字段名为 ref_papers (下划线风格)
            report_data = report.model_dump(by_alias=False)
            # 确保 user_id 正确
            if not report_data.get("user_id"):
                report_data["user_id"] = user_profile.info.id
            
            self.db.table("reports").insert(report_data).execute()
        except Exception as e:
            # [Mod] 暂时注释掉 system_logs 写入，改为直接打印，避免表不存在报错
            print(f"Error saving report: {str(e)}")
            # self._log_error("pipeline", f"Error saving report: {str(e)}", {"report_id": report.id})
            
        # 6. 发送邮件
        self.send_report_email_advanced(report, papers, user_profile.info.email)
        
        # 提取 usage
        usage = llm_result.get("_usage", {})
        return report, usage

    def send_report_email_advanced(self, report: Report, papers: List[PersonalizedPaper], user_email: str) -> bool:
        """
        使用高级格式化发送报告邮件。

        Args:
            report (Report): 报告对象
            papers (List[PersonalizedPaper]): 论文列表
            user_email (str): 用户邮箱

        Returns:
            bool: 发送是否成功
        """
        try:
            # 检查用户设置
            if not self._should_send_email(report.user_id, user_email):
                return False
            
            # 格式化邮件
            formatter = EmailFormatter()
            html_content, plain_content, stats = formatter.format_report_to_html(report, papers)
            
            # 发送邮件
            subject = f"【玻尔平台论文日报】{report.date}"
            success, msg = email_sender.send_email(user_email, subject, html_content, plain_content)
            
            if success:
                self._log_email_event(report.id, report.user_id, "sent", {"stats": stats})
            else:
                # [Mod] 暂时注释掉 system_logs 写入
                print(f"Failed to send email: {msg}")
                # self._log_error("email", f"Failed: {msg}", {"report_id": report.id})
            
            return success
            
        except Exception as e:
            # [Mod] 暂时注释掉 system_logs 写入
            print(f"Exception sending email: {str(e)}")
            # self._log_error("email", f"Exception: {str(e)}", {"report_id": report.id})
            return False

    def _should_send_email(self, user_id: str, user_email: str) -> bool:
        """
        检查用户是否应该接收邮件。

        Args:
            user_id (str): 用户ID
            user_email (str): 用户邮箱

        Returns:
            bool: 是否发送
        """
        if not user_email:
            return False
            
        return True

    def _log_email_event(self, report_id: str, user_id: str, event_type: str, event_data: Dict = None):
        """
        记录邮件事件到 email_analytics 表。

        Args:
            report_id (str): 报告ID
            user_id (str): 用户ID
            event_type (str): 事件类型 ('sent', 'opened', 'clicked')
            event_data (Dict, optional): 额外数据
        """
        try:
            self.db.table("email_analytics").insert({
                "report_id": report_id,
                "user_id": user_id,
                "event_type": event_type,
                "event_data": event_data or {}
            }).execute()
        except Exception as e:
            print(f"Error logging email event: {e}")

    def _log_error(self, source: str, message: str, meta: Dict):
        """
        记录错误到 system_logs 表。

        Args:
            source (str): 错误来源
            message (str): 错误信息
            meta (Dict): 上下文元数据
        """
        try:
            # [Mod] 暂时注释掉 system_logs 写入，避免表不存在报错
            print(f"ERROR [{source}]: {message} | Meta: {meta}")
            # self.db.table("system_logs").insert({
            #     "level": "ERROR",
            #     "source": source,
            #     "message": message,
            #     "meta": meta
            # }).execute()
        except Exception as e:
            print(f"CRITICAL: Failed to log error: {e}")

    def submit_feedback(self, report_id: str, user_id: str, rating: int, feedback_text: str = None) -> bool:
        """
        提交报告反馈。

        Args:
            report_id (str): 报告ID
            user_id (str): 用户ID
            rating (int): 评分 (1-5)
            feedback_text (str, optional): 反馈文本

        Returns:
            bool: 提交是否成功
        """
        try:
            if not 1 <= rating <= 5:
                raise ValueError("Rating must be 1-5")
            
            self.db.table("report_feedback").upsert({
                "report_id": report_id,
                "user_id": user_id,
                "rating": rating,
                "feedback_text": feedback_text
            }, on_conflict="report_id,user_id").execute()
            
            return True
        except Exception as e:
            self._log_error("feedback", f"Failed to submit: {str(e)}", {"report_id": report_id})
            return False

    def resend_daily_report(self, report_id: str) -> bool:
        """
        从数据库重新获取报告和相关论文，并发送邮件。
        用于验证"从数据库获取内容并发送"的逻辑，或用于重发失败的邮件。

        Args:
            report_id (str): 报告ID

        Returns:
            bool: 发送是否成功
        """
        try:
            print(f"Resending report {report_id}...")
            # 1. 获取报告
            report_res = self.db.table("reports").select("*").eq("id", report_id).execute()
            if not report_res.data:
                print(f"Report {report_id} not found.")
                return False
            
            report_data = report_res.data[0]
            # 构造 Report 对象 (注意处理字段名差异，如 ref_papers vs refPapers)
            # 数据库中是 ref_papers (snake_case)，Report 模型也是 ref_papers (by_alias=False时)
            # 但 Report 模型的 alias 是 refPapers。
            # Pydantic v2 model_validate 应该能处理
            report = Report(**report_data)
            
            # 2. 获取关联论文 ID
            paper_ids = report.ref_papers
            if not paper_ids:
                print("No ref_papers in report.")
                return False
                
            # 3. 获取论文详情 (从 papers 表)
            papers_res = self.db.table("papers").select("*").in_("id", paper_ids).execute()
            papers_data = papers_res.data
            
            # 4. 获取用户对这些论文的状态 (为了 relevance_score 和 why_this_paper)
            states_res = self.db.table("user_paper_states") \
                .select("*") \
                .eq("user_id", report.user_id) \
                .in_("paper_id", paper_ids) \
                .execute()
            states_map = {s["paper_id"]: s for s in states_res.data}
            
            # 5. 重构 PersonalizedPaper 列表
            from app.services.paper_service import paper_service
            papers = []
            for p_data in papers_data:
                state_data = states_map.get(p_data["id"])
                paper_obj = paper_service.merge_paper_state(p_data, state_data)
                papers.append(paper_obj)
            
            # 6. 发送邮件
            # 确保有邮箱
            if not report.email:
                # 尝试从 UserProfile 获取
                from app.services.user_service import user_service
                profile = user_service.get_profile(report.user_id)
                if profile and profile.info.email:
                    report.email = profile.info.email
                else:
                    print("No email address found for report.")
                    return False
            
            print(f"Sending email to {report.email}...")
            return self.send_report_email_advanced(report, papers, report.email)
            
        except Exception as e:
            print(f"Error resending report: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_report_by_id(self, report_id: str) -> Optional[Report]:
        """
        根据 ID 获取单个报告的详细信息。

        Args:
            report_id (str): 报告的唯一标识符。

        Returns:
            Optional[Report]: 如果找到则返回报告对象，否则返回 None。
        """
        try:
            response = self.db.table("reports").select("*").eq("id", report_id).execute()
            if response.data:
                return Report(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching report {report_id}: {e}")
            return None

report_service = ReportService()
