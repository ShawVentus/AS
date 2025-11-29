import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent / "backend"
sys.path.append(str(backend_dir))

try:
    from app.services.user_service import user_service
    from app.services.mock_data import USER_PROFILE
    from app.schemas.user import UserProfile as UserProfileSchema

    print("--- Testing Mock Data ---")
    try:
        print("Mock Data:", USER_PROFILE)
        profile = UserProfileSchema(**USER_PROFILE)
        print("Mock Data Validation: SUCCESS")
    except Exception as e:
        print("Mock Data Validation: FAILED")
        print(e)

    print("\n--- Testing Database Data ---")
    try:
        # Try to get the default user profile
        profile = user_service.get_profile()
        print("Database Data Retrieval: SUCCESS")
        print(profile)
    except Exception as e:
        print("Database Data Retrieval: FAILED")
        print(e)
        import traceback
        traceback.print_exc()

except Exception as e:
    print("Import Error or Setup Error:")
    print(e)
    import traceback
    traceback.print_exc()
