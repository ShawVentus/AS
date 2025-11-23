import sys
import os

output_file = os.path.join(os.path.dirname(__file__), "deps_status.txt")

with open(output_file, "w") as f:
    f.write(f"Python executable: {sys.executable}\n")
    
    try:
        import supabase
        f.write("supabase: OK\n")
    except ImportError as e:
        f.write(f"supabase: MISSING ({e})\n")

    try:
        import openai
        f.write("openai: OK\n")
    except ImportError as e:
        f.write(f"openai: MISSING ({e})\n")

    try:
        import apscheduler
        f.write("apscheduler: OK\n")
    except ImportError as e:
        f.write(f"apscheduler: MISSING ({e})\n")
        
    try:
        import jinja2
        f.write("jinja2: OK\n")
    except ImportError as e:
        f.write(f"jinja2: MISSING ({e})\n")
