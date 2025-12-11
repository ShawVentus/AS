import sys
import os
from dotenv import load_dotenv

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.services.report_service import report_service
from app.core.database import get_db

def test_resend_report_from_db():
    print("🚀 Testing Resend Report from DB...")
    
    db = get_db()
    
    # 1. Find the latest report
    try:
        print("🔍 Finding latest report...")
        # Get latest report that has ref_papers
        res = db.table("reports").select("id, date, title, email").order("created_at", desc=True).limit(1).execute()
        
        if not res.data:
            print("❌ No reports found in database.")
            return
            
        latest_report = res.data[0]
        report_id = latest_report["id"]
        print(f"📄 Found Report: {latest_report['title']} ({latest_report['date']})")
        print(f"🆔 ID: {report_id}")
        print(f"📧 Original Email: {latest_report.get('email')}")
        
        # Optional: Override email for testing if needed, but report_service uses report.email
        # If we want to test sending to ME (the developer), we might need to hack it or ensure the report is mine.
        # But user asked to "automatically get... and send to corresponding email".
        # So we should respect the email in the report.
        
        # 2. Call resend
        print("🔄 Calling resend_daily_report...")
        success = report_service.resend_daily_report(report_id)
        
        if success:
            print("✅ Resend Successful!")
        else:
            print("❌ Resend Failed.")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_resend_report_from_db()
