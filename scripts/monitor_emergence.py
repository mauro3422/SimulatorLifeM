import os
import time
import json
import runpy
import sys
import datetime

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
UNKNOWN_MOL_PATH = os.path.join(DATA_DIR, "unknown_molecules.json")
SCRIPTS_DIR = os.path.dirname(__file__)
MASS_AUDIT_SCRIPT = os.path.join(SCRIPTS_DIR, "mass_audit.py")
SCIENTIFIC_AUDIT_SCRIPT = os.path.join(SCRIPTS_DIR, "scientific_audit.py")

def check_for_unknowns():
    """Checks if there are unknown molecules waiting to be processed."""
    if not os.path.exists(UNKNOWN_MOL_PATH):
        return 0, 0
    
    try:
        with open(UNKNOWN_MOL_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            total = data.get("summary", {}).get("total_incognitas", 0)
            molecules_count = len(data.get("unknown_molecules", []))
            return total, molecules_count
    except Exception as e:
        print(f"Error reading unknown molecules: {e}")
        return 0, 0

def run_pipeline():
    """Runs the audit pipeline."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] 🚨 NEW MOLECULES DETECTED! Starting Analysis Pipeline...", flush=True)

    # 1. Mass Audit (Harvesting)
    print("   -> Running Mass Audit (Harvesting)...", flush=True)
    try:
        # We use run_path to execute the scripts in their own context but within this process
        runpy.run_path(MASS_AUDIT_SCRIPT, run_name="__main__")
    except Exception as e:
        print(f"   ❌ Mass Audit Failed: {e}")
        return

    # 2. Scientific Audit (Classification & Candidate Search)
    print("   -> Running Scientific Audit (Analysing)...", flush=True)
    try:
         runpy.run_path(SCIENTIFIC_AUDIT_SCRIPT, run_name="__main__")
    except Exception as e:
        print(f"   ❌ Scientific Audit Failed: {e}")
        return
        
    print(f"[{timestamp}] ✅ Pipeline Complete. Waiting for next batch...", flush=True)

def monitor_loop():
    print("==================================================")
    print("   🧪 LIFE SIMULATOR: MOLECULE EMERGENCE MONITOR   ")
    print("==================================================")
    print(f"Watching: {UNKNOWN_MOL_PATH}")
    print("Press Ctrl+C to stop.\n")

    last_count = 0

    try:
        while True:
            total_incognitas, list_count = check_for_unknowns()
            
            # If we find actual molecules in the list (not just the counter being high)
            if list_count > 0:
                print(f"🔎 Detected {list_count} new unknown molecules.")
                run_pipeline()
                last_count = 0 # Reset because pipeline clears the file
            
            time.sleep(2) 
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped.")

if __name__ == "__main__":
    monitor_loop()
