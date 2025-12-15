import os
import sys
import json
from datetime import datetime

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.core.database import get_db

def check_latest_progress():
    db = get_db()
    
    # Get latest execution
    print("Fetching latest execution...")
    exec_res = db.table("workflow_executions").select("*").order("created_at", desc=True).limit(1).execute()
    
    if not exec_res.data:
        print("No executions found.")
        return
        
    latest_exec = exec_res.data[0]
    exec_id = latest_exec["id"]
    print(f"Latest Execution ID: {exec_id}")
    print(f"Status: {latest_exec.get('status')}")
    print(f"Created At: {latest_exec.get('created_at')}")
    
    # Get steps
    print("\nFetching steps...")
    steps_res = db.table("workflow_steps").select("*").eq("execution_id", exec_id).order("step_order").execute()
    
    if not steps_res.data:
        print("No steps found for this execution.")
        return
        
    for step in steps_res.data:
        print(f"\nStep: {step['step_name']} (Status: {step['status']})")
        print(f"Progress: {step.get('progress')}")

if __name__ == "__main__":
    check_latest_progress()
