from typing import List, Optional
from datetime import datetime
import json
import os
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper
from app.schemas.user import UserProfile
from app.services.llm_service import llm_service
from app.utils.email_sender import email_sender
from app.core.database import get_db
import uuid

class ReportService:
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

    def generate_daily_report(self, papers: List[PersonalizedPaper], user_profile: UserProfile) -> Report:
        """
        使用 LLM 根据提供的论文列表生成每日总结报告。
        
        该方法会将生成的报告保存到数据库。

        Args:
            papers (List[PersonalizedPaper]): 用于生成报告的论文列表。
            user_profile (UserProfile): 用户画像，用于定制报告内容。

        Returns:
            Report: 生成的报告对象。
        """
        # 1. 将论文转换为字典列表供LLM使用
        # 适配新结构：展平数据供 prompt 使用
        papers_data = []
        for p in papers:
            flat_p = p.meta.model_dump()
            if p.analysis:
                flat_p.update(p.analysis.model_dump())
            if p.user_state:
                flat_p.update(p.user_state.model_dump())
            papers_data.append(flat_p)
        
        # 2. 调用LLM生成报告
        # 我们将user_profile序列化为字符串供提示词使用
        profile_str = json.dumps(user_profile.model_dump(), ensure_ascii=False, indent=2)
        
        llm_result = llm_service.generate_report(papers_data, profile_str)
        print(f"DEBUG: LLM Report Result: {json.dumps(llm_result, ensure_ascii=False, indent=2)}")
        
        # 3. 构建 Report 对象
        # LLM失败时的退路
        if not llm_result:
            llm_result = {
                "title": f"{datetime.now().strftime('%Y/%m/%d')} - Daily Report (Fallback)",
                "summary": "Failed to generate report via LLM.",
                "content": []
            }
            
        report = Report(
            id=str(uuid.uuid4()),
            user_id=user_profile.info.id, # 使用用户ID
            title=llm_result.get("title", "Daily Report"),
            date=datetime.now().strftime("%Y-%m-%d"),
            summary=llm_result.get("summary", ""),
            content=llm_result.get("content", []),
            ref_papers=llm_result.get("ref_papers", [])  # 新增: 提取引用论文列表
        )
        
        # 4. 保存到数据库
        try:
            # 我们需要正确处理user_id。
            # 对于MVP,我们可能只是将它链接到默认用户。
            # 但Report模型需要user_id。
            # 让我们先获取默认用户id。
            user_response = self.db.table("users").select("id").eq("email", user_profile.info.email).execute()
            if user_response.data:
                real_user_id = user_response.data[0]["id"]
                
                report_data = report.model_dump()
                report_data["user_id"] = real_user_id
                
                self.db.table("reports").insert(report_data).execute()
        except Exception as e:
            print(f"Error saving report: {e}")
            
        return report

    def send_email(self, report: Report, email: str) -> bool:
        """
        将生成的报告通过电子邮件发送给指定用户。

        Args:
            report (Report): 要发送的报告对象。
            email (str): 接收报告的电子邮件地址。

        Returns:
            bool: 发送是否成功。
        """
        try:
            # 渲染HTML
            # frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
            frontend_url = "http://localhost:5173" 
            html_content = email_sender.render_template("report.html", {
                "title": report.title,
                "date": report.date,
                "summary": report.summary,
                "content": report.content,
                "frontend_url": f"{frontend_url}/reports/{report.id}"
            })
            
            # 确定收件人
            recipients = [email]
            env_recipients = os.getenv("RECIPIENT_EMAILS")
            if env_recipients:
                # 按逗号分割并去除空白
                extra_emails = [e.strip() for e in env_recipients.split(",") if e.strip()]
                recipients.extend(extra_emails)
            
            # 去重
            recipients = list(set(recipients))
            
            # 发送给所有人
            print(f"Sending report to: {recipients}")
            # 使用批量发送或循环
            # 现在,循环就可以
            all_success = True
            for recipient in recipients:
                success, msg = email_sender.send_email(recipient, report.title, html_content)
                if not success:
                    print(f"Email send failed for {recipient}: {msg}")
                    all_success = False
                    
            return all_success
        except Exception as e:
            print(f"Error sending email: {e}")
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
