from typing import List, Optional
from datetime import datetime
import json
import os
from schemas.report import Report
from schemas.paper import Paper
from schemas.user import UserProfile
from services.mock_data import MOCK_REPORTS
from services.llm_service import llm_service
from utils.email_sender import email_sender
from database import get_db
import uuid

class ReportService:
    def __init__(self):
        self.db = get_db()

    def get_reports(self) -> List[Report]:
        """从数据库获取所有报告"""
        try:
            response = self.db.table("reports").select("*").order("date", desc=True).execute()
            if response.data:
                return [Report(**r) for r in response.data]
            return []
        except Exception as e:
            print(f"Error fetching reports: {e}")
            return []

    def generate_daily_report(self, papers: List[Paper], user_profile: UserProfile) -> Report:
        """
        使用LLM生成每日报告
        """
        # 1. 将论文转换为字典列表供LLM使用
        papers_data = [p.model_dump() for p in papers]
        
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
            user_id=user_profile.info.email, # 现在使用email作为ID代理(如果需要),或者只生成UUID
            title=llm_result.get("title", "Daily Report"),
            date=datetime.now().strftime("%Y-%m-%d"),
            summary=llm_result.get("summary", ""),
            content=llm_result.get("content", [])
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
        通过邮件发送报告
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
        try:
            response = self.db.table("reports").select("*").eq("id", report_id).execute()
            if response.data:
                return Report(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching report {report_id}: {e}")
            return None

report_service = ReportService()
