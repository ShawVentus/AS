import os
import sys
import json
from datetime import datetime

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import get_db
from app.services.workflow_engine import WorkflowEngine
from app.core.workflow_step import WorkflowStep

class TestStep(WorkflowStep):
    name = "test_step"
    def execute(self, context):
        return {}

def test_progress_column():
    print("Testing progress column existence and functionality...")
    
    engine = WorkflowEngine()
    execution_id = engine.create_execution("test_workflow")
    print(f"Created execution: {execution_id}")
    
    step = TestStep()
    engine.steps = [step]
    
    # Manually create step record
    engine._create_step_record(step, 0)
    print("Created step record.")
    
    # Try to update progress directly via Supabase client
    try:
        progress_data = {"current": 50, "total": 100, "message": "Testing progress"}
        
        # Get step ID
        step_id_response = get_db().table("workflow_steps").select("id").eq("execution_id", execution_id).eq("step_name", step.name).execute()
        if not step_id_response.data:
            print("❌ Could not find step record.")
            return
            
        step_id = step_id_response.data[0]["id"]
        print(f"Found step ID: {step_id}")
        
        # Update progress
        get_db().table("workflow_steps").update({
            "progress": progress_data
        }).eq("id", step_id).execute()
        print("Successfully executed update query.")
        
        # Verify by reading back
        response = get_db().table("workflow_steps").select("progress").eq("id", step_id).execute()
        
        if response.data:
            saved_progress = response.data[0].get("progress")
            print(f"Read back progress: {saved_progress}")
            if saved_progress == progress_data:
                print("✅ Progress column exists and works correctly!")
            else:
                print(f"❌ Progress data mismatch. Expected {progress_data}, got {saved_progress}")
        else:
            print("❌ Could not find step record to verify.")
            
    except Exception as e:
        print(f"❌ Error updating progress: {e}")
        print("This likely means the 'progress' column is missing.")

if __name__ == "__main__":
    test_progress_column()
