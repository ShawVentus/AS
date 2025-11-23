import subprocess
import sys
import os
import time

STEPS = [
    ("step1_crawl.py", "Crawling Papers"),
    ("step2_analyze.py", "Analyzing Papers (LLM)"),
    ("step3_report.py", "Generating Report"),
    ("step4_email.py", "Sending Email")
]

def run_step(script_name, description):
    print(f"\n{'='*60}")
    print(f"🚀 Running {description}...")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Run script using the same python interpreter
    result = subprocess.run([sys.executable, script_name], cwd=os.path.dirname(__file__))
    
    duration = time.time() - start_time
    
    if result.returncode != 0:
        print(f"\n❌ {description} FAILED with exit code {result.returncode}")
        sys.exit(result.returncode)
    else:
        print(f"\n✅ {description} COMPLETED in {duration:.2f}s")

def main():
    log_file = os.path.join(os.path.dirname(__file__), "e2e_execution.log")
    
    with open(log_file, "w") as f:
        f.write("Starting E2E Verification Suite...\n")
        f.write(f"Python Executable: {sys.executable}\n")
        
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(data_dir):
            f.write(f"Creating data directory: {data_dir}\n")
            os.makedirs(data_dir)
        
        for script, desc in STEPS:
            f.write(f"\n{'='*60}\n")
            f.write(f"🚀 Running {desc}...\n")
            f.write(f"{'='*60}\n")
            
            start_time = time.time()
            
            # Run script using the same python interpreter
            # Capture output
            result = subprocess.run(
                [sys.executable, script], 
                cwd=os.path.dirname(__file__),
                capture_output=True,
                text=True
            )
            
            f.write(result.stdout)
            f.write(result.stderr)
            
            duration = time.time() - start_time
            
            if result.returncode != 0:
                f.write(f"\n❌ {desc} FAILED with exit code {result.returncode}\n")
                print(f"FAILED: {desc}") # Keep console output just in case
                sys.exit(result.returncode)
            else:
                f.write(f"\n✅ {desc} COMPLETED in {duration:.2f}s\n")
                
        f.write(f"\n{'='*60}\n")
        f.write("🎉 All steps completed successfully!\n")
        f.write(f"{'='*60}\n")
        print("SUCCESS")

if __name__ == "__main__":
    main()
