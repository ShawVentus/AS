import sys
import os
import json
import asyncio

# 将backend添加到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.report_service import report_service
from schemas.report import Report
from core.config import settings

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE = os.path.join(DATA_DIR, "3_report_results.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "4_email_status.json")

async def run_step4():
    print("=== Step 4: Send Email ===")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        sys.exit(1)
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        report_data = json.load(f)
        
    report = Report(**report_data)
    
    # 使用配置的收件人或退回默认值
    recipient = settings.RECIPIENT_EMAILS or "test@example.com"
    print(f"Sending email to: {recipient}")
    
    try:
        # send_email期望Report对象,而不ID
        success = report_service.send_email(report, recipient)
            
        status = {
            "success": success,
            "recipient": recipient,
            "report_id": report.id,
            "timestamp": report.date
        }
        
        if success:
            print("✅ Email sent successfully!")
        else:
            print("❌ Email sending failed (check logs/console).")
            sys.exit(1)
            
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
            
        print(f"Saved results to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_step4())
