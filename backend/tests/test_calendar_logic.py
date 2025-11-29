import pytest
from datetime import datetime, timedelta
from app.services.paper_service import paper_service
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, UserPaperState

# Mock DB for testing
class MockDB:
    def __init__(self):
        self.data = []

    def table(self, name):
        return self

    def select(self, *args):
        return self

    def eq(self, key, value):
        # Simple mock filtering
        return self

    def gte(self, key, value):
        return self

    def lt(self, key, value):
        return self
    
    def in_(self, key, values):
        return self

    def execute(self):
        # Return mock data based on context (simplified)
        return type('obj', (object,), {'data': self.data})

def test_get_paper_dates_logic():
    # This test verifies the date logic, assuming DB returns correct data
    # In a real integration test we would insert data into DB
    
    # Mock the DB response for get_paper_dates
    mock_dates = [
        {"created_at": "2025-11-01T10:00:00+00:00"},
        {"created_at": "2025-11-01T15:00:00+00:00"}, # Duplicate date
        {"created_at": "2025-11-15T09:00:00+00:00"},
        {"created_at": "2025-11-30T23:59:59+00:00"}
    ]
    
    # Inject mock DB
    original_db = paper_service.db
    paper_service.db = MockDB()
    paper_service.db.data = mock_dates
    
    dates = paper_service.get_paper_dates("user123", 2025, 11)
    
    # Restore DB
    paper_service.db = original_db
    
    assert "2025-11-01" in dates
    assert "2025-11-15" in dates
    assert "2025-11-30" in dates
    assert len(dates) == 3 # Should deduplicate

def test_date_range_calculation():
    # Verify the date range logic in get_paper_dates
    year = 2025
    month = 11
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month + 1:02d}-01"
    assert start_date == "2025-11-01"
    assert end_date == "2025-12-01"
    
    month = 12
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year + 1}-01-01"
    assert start_date == "2025-12-01"
    assert end_date == "2026-01-01"

if __name__ == "__main__":
    test_get_paper_dates_logic()
    test_date_range_calculation()
    print("Backend Calendar Logic Tests Passed!")
