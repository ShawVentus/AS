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
from app.utils.error_notifier import error_notifier
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

    def get_reports(self, user_id: str) -> List[Report]:
        """
        从数据库获取指定用户的报告。

        Args:
            user_id (str): 用户ID

        Returns:
            List[Report]: 该用户的报告对象列表,按日期倒序排列。
        """
        try:
            response = self.db.table("reports")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .execute()
            if response.data:
                return [Report(**r) for r in response.data]
            return []
        except Exception as e:
            print(f"Error fetching reports: {e}")
            return []

    def generate_daily_report(self, papers: List[PersonalizedPaper], user_profile: UserProfile, 
                              custom_title: Optional[str] = None, manual_query: Optional[str] = None,
                              context: Optional[Dict[str, Any]] = None) -> tuple[Report, Dict[str, int]]:
        """
        生成每日报告并自动发送邮件。
        Generate daily report and send email automatically.

        Args:
            papers (List[PersonalizedPaper]): 用于生成报告的论文列表 (List of papers for the report)。
            user_profile (UserProfile): 用户画像，用于定制报告内容 (User profile for customization)。
            custom_title (Optional[str]): 自定义报告标题 (Custom report title)。
            manual_query (Optional[str]): 手动输入的查询 (Manual query for instant report)。
            context (Optional[Dict[str, Any]]): 工作流上下文，包含 crawled_count 等信息

        Returns:
            tuple[Report, Dict[str, int]]: 生成的报告对象和 Usage 统计 (Generated report object and usage stats)。
        """
        # 0. 应用统一的数量限制
        limit = int(os.environ.get("REPORT_PAPER_LIMIT", 15))
        
        # 按相关性排序（PersonalizedPaper 对象中 user_state 可能为 None）
        sorted_papers = sorted(
            papers, 
            key=lambda p: p.user_state.relevance_score if p.user_state else 0.0, 
            reverse=True
        )
        
        # 截断
        if len(sorted_papers) > limit:
            print(f"[INFO] Truncating papers from {len(sorted_papers)} to {limit} for report generation.")
            target_papers = sorted_papers[:limit]
        else:
            target_papers = sorted_papers

        # 1. 准备数据供 LLM 使用
        papers_data = []
        for p in target_papers:
            flat_p = p.meta.model_dump()
            if p.analysis:
                flat_p.update(p.analysis.model_dump())
            if p.user_state:
                flat_p.update(p.user_state.model_dump())
            papers_data.append(flat_p)
        
        # 2. 调用 LLM 生成报告
        profile_dict = user_profile.model_dump()
        
        # [Manual Override] Inject manual query into profile dict
        if manual_query:
            # Completely replace context to avoid "contamination" from old profile
            profile_dict["context"] = {
                "preferences": "User is requesting an instant report on a specific topic.",
                "currentTask": f"Researching: {manual_query}",
                "futureGoal": "Get a quick overview of the latest papers on this topic."
            }
            
            # Re-construct focus to only include manual query
            # We keep the structure but clear the lists
            profile_dict["focus"] = {
                "category": [], 
                "keywords": [manual_query],
                "authors": [],
                "institutions": [],
                "description": manual_query, # Explicitly set description
                "manual_query_instruction": f"User explicitly requested a report on: '{manual_query}'. Please focus the summary ONLY on this topic and IGNORE any previous user context."
            }
        else:
            # 正常模式：格式化 preferences 列表为 Markdown
            if "context" in profile_dict and "preferences" in profile_dict["context"]:
                prefs = profile_dict["context"]["preferences"]
                
                # 格式化列表为 Markdown 无序列表
                if isinstance(prefs, list) and prefs:
                    formatted = "\n".join([f"- {p}" for p in prefs])
                    profile_dict["context"]["preferences"] = formatted
                    print(f"[报告生成] 格式化 preferences: {len(prefs)} 条")
                elif isinstance(prefs, list) and not prefs:
                    # 空列表
                    profile_dict["context"]["preferences"] = "（用户未设置研究偏好）"
            
        profile_str = json.dumps(profile_dict, ensure_ascii=False, indent=2)
        llm_result = llm_service.generate_report(papers_data, profile_str)
        print(f"DEBUG: LLM Report Result: {json.dumps(llm_result, ensure_ascii=False, indent=2)}")
        
        # LLM 失败时的退路
        if not llm_result or not llm_result.get("title"):
            error_msg = f"LLM报告生成失败，用户: {user_profile.info.name} ({user_profile.info.id})"
            print(f"❌ {error_msg}")
            
            # 发送错误通知邮件
            import traceback
            error_notifier.notify_critical_error(
                error_type="REPORT_GENERATION_FAILED",
                error_message=error_msg,
                context={
                    "user_id": user_profile.info.id,
                    "user_name": user_profile.info.name,
                    "user_email": user_profile.info.email,
                    "manual_query": manual_query,
                    "papers_count": len(papers),
                    "failed_at": datetime.now().isoformat()
                },
                stack_trace=traceback.format_exc() if traceback else None
            )

            llm_result = {
                "title": f"{datetime.now().strftime('%Y/%m/%d')} - Daily Report (Fallback)",
                "summary": "Failed to generate report via LLM.",
                "content": "No content generated.",
                "ref_papers": []
            }
            
            
        # 3. 获取 ArXiv 日期作为报告日期
        # 优先从 system_status 获取最新 ArXiv 日期，否则使用系统日期
        try:
            status_res = self.db.table("system_status").select("value").eq("key", "latest_arxiv_date").execute()
            if status_res.data:
                report_date = status_res.data[0]["value"]
                print(f"使用 ArXiv 日期作为报告日期: {report_date}")
            else:
                report_date = datetime.now().strftime("%Y-%m-%d")
                print(f"警告: 未找到 ArXiv 日期，使用系统日期: {report_date}")
        except Exception as e:
            print(f"获取 ArXiv 日期失败: {e}")
            report_date = datetime.now().strftime("%Y-%m-%d")
        
        # 4. 计算统计数据
        # 区分自动任务和手动任务的统计逻辑
        # 【修复】传递 context 给 _calculate_paper_statistics
        total_count, recommended_count = self._calculate_paper_statistics(
            papers=papers,
            user_id=user_profile.info.id,
            is_manual_task=bool(manual_query),
            report_date=report_date,
            context=context  # ← 添加这个参数！
        )
        
        # 5. 创建 Report 对象
        # Use custom_title if provided, otherwise use LLM result title
        final_title = custom_title if custom_title else llm_result.get("title", "Daily Report")
        
        report = Report(
            id=str(uuid.uuid4()),
            user_id=user_profile.info.id,
            email=user_profile.info.email,  # [Add] 填充 email 字段
            title=final_title,
            date=report_date, # [MODIFIED] 使用 ArXiv 日期
            summary=llm_result.get("summary", ""),
            content=llm_result.get("content", ""),
            ref_papers=llm_result.get("ref_papers", []),
            total_papers_count=total_count,
            recommended_papers_count=recommended_count
        )
        
        # 6. 保存到数据库
        try:
            # [Fix] 使用 by_alias=False 确保使用 Python 属性名 (ref_papers) 而不是别名 (refPapers)
            # 假设数据库字段名为 ref_papers (下划线风格)
            report_data = report.model_dump(by_alias=False)
            # 确保 user_id 正确
            if not report_data.get("user_id"):
                report_data["user_id"] = user_profile.info.id
            
            # 【修复】添加 created_at 字段，避免数据库非空约束错误
            report_data["created_at"] = datetime.now().isoformat()
            
            self.db.table("reports").insert(report_data).execute()
        except Exception as e:
            print(f"Error saving report: {str(e)}")
            self._log_error("pipeline", f"Error saving report: {str(e)}", {"report_id": report.id})
            
        # 7. 发送邮件
        # 【修复】传递正确的统计数据给邮件格式化器
        self.send_report_email_advanced(report, papers, user_profile.info.email, 
                                        total_count=total_count, 
                                        recommended_count=recommended_count)
        
        # 提取 usage
        usage = llm_result.get("_usage", {})
        return report, usage

    def send_report_email_advanced(self, report: Report, papers: List[PersonalizedPaper], user_email: str,
                                   total_count: int = None, recommended_count: int = None) -> bool:
        """
        使用高级格式化发送报告邮件。

        Args:
            report (Report): 报告对象
            papers (List[PersonalizedPaper]): 论文列表
            user_email (str): 用户邮箱
            total_count (int, optional): 爬取的总论文数（用于邮件统计）
            recommended_count (int, optional): 推荐的论文数（用于邮件统计）

        Returns:
            bool: 发送是否成功
        """
        try:
            # 检查用户设置
            if not self._should_send_email(report.user_id, user_email):
                return False
            
            # 格式化邮件，传递统计数据
            formatter = EmailFormatter()
            html_content, plain_content, stats = formatter.format_report_to_html(
                report, papers, 
                total_count=total_count, 
                recommended_count=recommended_count
            )
            
            # 发送邮件
            subject = f"【ArxivScout论文日报】{report.date}"
            success, msg = email_sender.send_email(user_email, subject, html_content, plain_content)
            
            if success:
                self._log_email_event(report.id, report.user_id, "sent", {"stats": stats})
            else:
                print(f"Failed to send email: {msg}")
                # 记录失败事件到 email_analytics
                self._log_email_event(report.id, report.user_id, "failed", {"error": msg, "stats": stats})
                # 记录错误到 system_logs
                self._log_error("email", f"Failed: {msg}", {"report_id": report.id, "user_email": user_email})
            
            return success
            
        except Exception as e:
            error_msg = f"发送报告邮件时发生异常: {str(e)}"
            print(error_msg)
            
            # 发送错误通知邮件
            import traceback
            error_notifier.notify_warning(
                error_type="REPORT_EMAIL_SENDING_FAILED",
                error_message=error_msg,
                context={
                    "report_id": report.id,
                    "user_id": report.user_id,
                    "user_email": user_email,
                    "report_title": report.title,
                    "failed_at": datetime.now().isoformat()
                },
                stack_trace=traceback.format_exc()
            )
            return False

    def _calculate_paper_statistics(self, papers: List[PersonalizedPaper], user_id: str, 
                                    is_manual_task: bool, report_date: Optional[str] = None,
                                    context: Optional[Dict[str, Any]] = None) -> tuple[int, int]:
        """
        计算论文统计数据（总数和推荐数）。
        
        根据任务类型采用不同的统计逻辑：
        - 自动任务：从数据库查询今日爬取的所有论文
        - 手动任务：从 context 读取爬虫抓取的总数（crawled_count）
        
        Args:
            papers (List[PersonalizedPaper]): 用于报告生成的论文列表
            user_id (str): 用户ID
            is_manual_task (bool): 是否为手动任务（即时报告）
            report_date (Optional[str]): 报告日期，用于查询今日论文，格式 YYYY-MM-DD
            context (Optional[Dict[str, Any]]): 工作流上下文，包含 crawled_count 等信息
            
        Returns:
            tuple[int, int]: (总论文数, 推荐论文数)
        """
        # 从配置读取推荐度阈值
        relevance_threshold = float(os.environ.get("RELEVANCE_THRESHOLD", "0.7"))
        
        if is_manual_task:
            # 【修复】手动任务：优先使用实际筛选数，确保报告数据准确
            # 数据优先级：actually_filtered_count > crawled_count > len(papers)
            # 
            # 说明：
            # - actually_filtered_count: 实际筛选的论文数（最准确，反映用户实际看到的论文）
            # - crawled_count: 爬虫提交的论文数（可能包含被分类过滤的论文）
            # - len(papers): 传入的论文列表长度（兜底方案）
            
            # [调试] 输出 context 详情，用于追踪数据来源
            print(f"[DEBUG] _calculate_paper_statistics 接收到的 context keys: {list(context.keys()) if context else 'None'}")
            print(f"[DEBUG] context 中的 crawled_count: {context.get('crawled_count', '未找到') if context else '未找到'}")
            print(f"[DEBUG] context 中的 actually_filtered_count: {context.get('actually_filtered_count', '未找到') if context else '未找到'}")
            
            if context and "actually_filtered_count" in context:
                # 最优：使用实际筛选的论文数（accepted + rejected）
                total_count = context["actually_filtered_count"]
                print(f"[INFO] 使用实际筛选数 (actually_filtered_count): {total_count}")
                
            elif context and "crawled_count" in context:
                # 次优：使用爬虫提交的论文数
                total_count = context["crawled_count"]
                print(f"[INFO] 使用爬虫统计数 (crawled_count): {total_count}")
                print(f"[WARN] 缺少 actually_filtered_count，可能有论文被分类过滤")
                
            else:
                # 兜底：使用传入的 papers 长度
                total_count = len(papers)
                print(f"[WARN] context 中无统计数据，使用 papers 长度: {total_count}")
            
            recommended_count = sum(
                1 for p in papers 
                if (p.user_state and p.user_state.relevance_score >= relevance_threshold)
            )
            print(f"[手动任务] 本次爬取论文数: {total_count}, 推荐论文数 (阈值>={relevance_threshold}): {recommended_count}")
            
        else:
            # 自动任务：查询今日创建的用户论文状态记录
            try:
                # 获取今日日期（如果未提供）
                if not report_date:
                    report_date = datetime.now().strftime("%Y-%m-%d")
                
                # 查询今日创建的用户论文状态记录
                today_states_res = self.db.table("user_paper_states") \
                    .select("paper_id, relevance_score") \
                    .eq("user_id", user_id) \
                    .gte("created_at", f"{report_date} 00:00:00") \
                    .lte("created_at", f"{report_date} 23:59:59") \
                    .execute()
                
                if today_states_res.data:
                    total_count = len(today_states_res.data)
                    recommended_count = sum(
                        1 for s in today_states_res.data 
                        if s.get("relevance_score", 0) >= relevance_threshold
                    )
                    print(f"[自动任务] 今日爬取论文数: {total_count}, 推荐论文数 (阈值>={relevance_threshold}): {recommended_count}")
                else:
                    # 数据库中没有今日数据，使用传入的 papers 作为备选
                    total_count = len(papers)
                    recommended_count = sum(
                        1 for p in papers 
                        if (p.user_state and p.user_state.relevance_score >= relevance_threshold)
                    )
                    print(f"[自动任务-备选] 未找到今日数据，使用传入论文数: {total_count}, 推荐数: {recommended_count}")
                    
            except Exception as e:
                # 查询失败时使用传入的 papers
                print(f"查询今日论文统计失败: {e}")
                total_count = len(papers)
                recommended_count = sum(
                    1 for p in papers 
                    if (p.user_state and p.user_state.relevance_score >= relevance_threshold)
                )
                print(f"[自动任务-异常备选] 使用传入论文数: {total_count}, 推荐数: {recommended_count}")
        
        return total_count, recommended_count

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
            print(f"ERROR [{source}]: {message} | Meta: {meta}")
            self.db.table("system_logs").insert({
                "level": "ERROR",
                "source": source,
                "message": message,
                "meta": meta
            }).execute()
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
