import sys
import os
from datetime import datetime
from typing import List

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.email_formatter import EmailFormatter
from app.schemas.report import Report
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, PaperLinks, UserPaperState, PaperAnalysis

def test_email_formatting():
    print("Testing Email Formatting...")
    
    # Mock Data
    links = PaperLinks(pdf="http://example.com/pdf", arxiv="http://example.com/arxiv")
    meta = RawPaperMetadata(
        id="123",
        title="Test Paper Title",
        authors=["Author A", "Author B"],
        published_date="2023-01-01",
        category=["cs.AI"],
        links=links,
        summary="Test Summary"
    )
    user_state = UserPaperState(
        paper_id="123",
        user_id="user1",
        relevance_score=0.9,
        why_this_paper="Good match",
        accepted=True
    )
    analysis = PaperAnalysis(
        paper_id="123",
        details={"tldr": "Too long; didn't read"}
    )
    
    paper = PersonalizedPaper(
        meta=meta,
        user_state=user_state,
        analysis=analysis
    )
    
    report = Report(
        id="report1",
        user_id="user1",
        email="test@example.com",
        title="Daily Report Test",
        date="2023-10-27",
        summary="Report Summary",
        content="Report Content",
        ref_papers=["123"],
        total_papers_count=1,
        recommended_papers_count=1
    )
    
    formatter = EmailFormatter()
    
    try:
        html, plain, stats = formatter.format_report_to_html(report, [paper])
        print("✅ Formatting Successful!")
        print(f"HTML Length: {len(html)}")
        print(f"Plain Text Length: {len(plain)}")
        print(f"Stats: {stats}")
        
        # Verify links in plain text
        if "http://example.com/arxiv" in plain:
            print("✅ Link found in plain text.")
        else:
            print("❌ Link NOT found in plain text.")
            
    except Exception as e:
        print(f"❌ Formatting Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_email_formatting()
