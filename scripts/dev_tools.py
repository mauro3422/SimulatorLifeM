"""
Developer Tools Suite - LifeSimulator
======================================
Consolidated Meta-Tools for Code Health, Auditing, and Statistics.

Usage:
    python scripts/dev_tools.py --mode audit   # Full code health audit
    python scripts/dev_tools.py --mode stats   # Show codebase statistics
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the auditor from its archived location
from scripts.archives.code_audit import CodeAuditor

def run_audit(root_path):
    """Run the full code audit."""
    print("=" * 60)
    print("🔍 CODE AUDIT - LifeSimulator Developer Suite")
    print("=" * 60)
    
    auditor = CodeAuditor(root_path)
    auditor.scan_directory()
    auditor.print_report()
    
    # Save report
    output_path = os.path.join(root_path, "scripts", "audit_report.txt")
    auditor.save_report(output_path)
    print(f"\n✅ Full report saved to: {output_path}")

def run_stats(root_path):
    """Show quick codebase statistics."""
    print("=" * 60)
    print("📊 CODEBASE STATISTICS - LifeSimulator")
    print("=" * 60)
    
    auditor = CodeAuditor(root_path)
    auditor.scan_directory()
    
    # Quick stats
    print(f"\n  Total Files:  {len(auditor.files)}")
    print(f"  Total Lines:  {auditor.total_lines:,}")
    print(f"  Total Size:   {auditor.total_bytes / 1024:.1f} KB")
    
    # Kernel count
    kernels = [f for f in auditor.get_function_report() if f[3]]
    print(f"  Taichi Kernels: {len(kernels)}")
    
    # Classes
    classes = auditor.get_class_report()
    print(f"  Classes:      {len(classes)}")

def main():
    parser = argparse.ArgumentParser(description="Developer Tools for LifeSimulator")
    parser.add_argument("--mode", choices=["audit", "stats"], default="stats",
                        help="Mode: 'audit' for full report, 'stats' for quick overview")
    args = parser.parse_args()
    
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if args.mode == "audit":
        run_audit(root_path)
    elif args.mode == "stats":
        run_stats(root_path)

if __name__ == "__main__":
    main()
