import sys
import os
from datetime import datetime
from typing import List
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.utils.email_formatter import EmailFormatter
from app.utils.email_sender import email_sender
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, PaperLinks, UserPaperState, PaperAnalysis

def test_real_email_send():
    print("🚀 Testing Real Email Sending...")
    
    # 1. Get Recipient
    recipient = os.getenv("RECIPIENT_EMAILS")
    if not recipient:
        print("❌ RECIPIENT_EMAILS not found in .env")
        return
    
    # Handle multiple recipients if comma separated
    recipient = recipient.split(',')[0].strip()
    print(f"📧 Target Recipient: {recipient}")
    
    # 2. Mock Data Construction
    print("🛠️ Constructing Mock Report Data...")
    links = PaperLinks(pdf="http://example.com/pdf", arxiv="https://arxiv.org/abs/2512.08185")
    meta = RawPaperMetadata(
        id="2512.08185",
        title="Test Paper: Medical LLM Safety Assessment",
        authors=["Author A", "Author B"],
        published_date="2025-12-10",
        category=["cs.AI", "cs.LG"],
        links=links,
        summary="This is a test summary for the email sending function verification."
    )
    user_state = UserPaperState(
        paper_id="2512.08185",
        user_id="test_user_id",
        relevance_score=0.95,
        why_this_paper="This paper is highly relevant to your interest in LLM safety.",
        accepted=True
    )
    analysis = PaperAnalysis(
        paper_id="2512.08185",
        details={"tldr": "A framework for assessing medical LLM safety."}
    )
    
    paper = PersonalizedPaper(
        meta=meta,
        user_state=user_state,
        analysis=analysis
    )
    
    report = Report(
        id="test_report_id",
        user_id="test_user_id",
        email=recipient,
        title="Test Daily Report - Email Verification",
        date=datetime.now().strftime("%Y-%m-%d"),
        summary="This is a test report generated to verify the email sending functionality. If you see this, the system is working correctly.",
        content="### Test Content\nThis email confirms that the email sender and formatter are working as expected.",
        ref_papers=["2512.08185"],
        total_papers_count=1,
        recommended_papers_count=1
    )
    
    # 3. Format Email
    print("🎨 Formatting Email...")
    formatter = EmailFormatter()
    try:
        html, plain, stats = formatter.format_report_to_html(report, [paper])
        print("✅ Formatting Successful")
    except Exception as e:
        print(f"❌ Formatting Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Send Email
    print("outbox 📤 Sending Email...")
    try:
        subject = f"【测试】邮件发送功能验证 {datetime.now().strftime('%H:%M:%S')}"
        success, msg = email_sender.send_email(recipient, subject, html, plain)
        
        if success:
            print(f"✅ Email Sent Successfully to {recipient}!")
        else:
            print(f"❌ Email Sending Failed: {msg}")
            
    except Exception as e:
        print(f"❌ Exception during sending: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_email_send()
