"""
LifeMonitor - Unified Diagnostic & Monitoring System
===================================================
The "Swiss Army Knife" for LifeSimulator health and performance.

Usage:
    python scripts/monitor.py --mode audit      # Full chemical health check
    python scripts/monitor.py --mode forensic   # Deep physics/Z-stability analysis
    python scripts/monitor.py --mode tune       # Fast parameter optimization
    python scripts/monitor.py --mode bench      # Hardware stress test (scaling)
"""

import sys
import os
import argparse
import time
import numpy as np

# Use OpenGL for broader compatibility in monitoring tools
import taichi as ti
ti.init(arch=ti.opengl, offline_cache=True)

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.systems.taichi_fields import (
    n_particles, pos, pos_z, atom_types, num_enlaces, enlaces_idx,
    molecule_id, is_active, total_bonds_count, next_molecule_id
)
from src.systems.simulation_gpu import (
    simulation_step_gpu, init_molecule_ids
)
from src.systems.molecular_analyzer import get_molecular_analyzer
from src.core.perf_logger import get_perf_logger
from src.config import system_constants as sys_cfg

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

class LifeMonitor:
    def __init__(self, mode="audit"):
        self.mode = mode
        self.analyzer = get_molecular_analyzer()
        self.perf = get_perf_logger()
        self.particles = 3000
        self.frames = 1000
        
        print(f"{BOLD}{CYAN}🚀 LifeMonitor System Ready (Mode: {mode.upper()}){RESET}")
    def run(self):
        if self.mode == "audit":
            self._run_audit()
        elif self.mode == "forensic":
            self._run_forensic()
        elif self.mode == "tune":
            print(f"{YELLOW}⚠ Running tune mode via legacy wrapper for speed...{RESET}")
            import subprocess
            subprocess.run([sys.executable, "scripts/archives/tune_vsepr.py"])
        elif self.mode == "bench":
            self._run_bench()

    def _setup_sim(self, p_count):
        n_particles[None] = p_count
        
        # Physics & Bounds
        from scripts.advanced_molecular_analyzer import init_simulation_gpu
        init_simulation_gpu(p_count)
        
        # Particle Data
        center = sys_cfg.WORLD_SIZE / 2
        pos_np = (np.random.rand(sys_cfg.MAX_PARTICLES, 2) * 500.0 + (center - 250.0)).astype(np.float32)
        pos.from_numpy(pos_np)
        
        types_np = np.random.choice(6, size=sys_cfg.MAX_PARTICLES).astype(np.int32)
        atom_types.from_numpy(types_np)
        
        is_active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
        is_active_np[:p_count] = 1
        is_active.from_numpy(is_active_np)
        
        # Molecule Initialization
        init_molecule_ids()
        ti.sync()

    def _run_audit(self):
        self._setup_sim(self.particles)
        print(f"🏃 Running {self.frames} frames for Chemical Audit...")
        
        self.analyzer.reset()
        start_time = time.time()
        
        for f in range(1, self.frames + 1):
            # Simulation Step
            self.perf.start("total")
            simulation_step_gpu(1)
            self.perf.stop("total")
            self.perf.end_frame()
            
            # Analysis every 50 frames
            if f % 50 == 0:
                ti.sync()
                self.analyzer.analyze_frame(
                    pos.to_numpy(), pos_z.to_numpy(), atom_types.to_numpy(),
                    enlaces_idx.to_numpy(), num_enlaces.to_numpy(),
                    molecule_id.to_numpy(), is_active.to_numpy()
                )
                if f % 250 == 0:
                    summary = self.analyzer.get_summary()
                    print(f"  [{f}/{self.frames}] Bonds: {total_bonds_count[None]:4d} | "
                          f"Emergence: {summary['emergence_velocity']:.1f} | "
                          f"Z-Stability: {summary['z_stability_avg']:.2f}")

        total_time = time.time() - start_time
        print(f"\n{BOLD}{GREEN}✅ Audit Complete!{RESET}")
        self._print_final_summary(total_time)

    def _run_bench(self):
        """Stress test with particle scaling."""
        print(f"{BOLD}⚙️ CALIBRATING HARDWARE (Particle Scaling Benchmark){RESET}")
        steps = [1000, 3000, 7000, 10000]
        results = []
        
        for p in steps:
            self._setup_sim(p)
            print(f"  Testing {p} particles...", end="", flush=True)
            t_start = time.time()
            simulation_step_gpu(100)
            ti.sync()
            t_end = time.time()
            fps = 100.0 / (t_end - t_start)
            results.append((p, fps))
            print(f" {GREEN}{fps:6.1f} FPS{RESET}")
            
        print(f"\n{BOLD}Hardware Limit Estimate:{RESET}")
        for p, fps in results:
            color = GREEN if fps > 60 else (YELLOW if fps > 30 else RED)
            print(f"  {p:6d} Particles: {color}{fps:6.1f} FPS{RESET}")

    def _print_final_summary(self, total_time):
        summary = self.analyzer.get_summary()
        print("\n" + "="*50)
        print(f"  {BOLD}LIFE MONITOR FINAL REPORT{RESET}")
        print("="*50)
        print(f"  Runtime:         {total_time:.2f}s")
        print(f"  Unique Formulas: {summary['unique_formulas']}")
        print(f"  Total Formed:    {summary['total_formations']}")
        print(f"  Emergence Vel:   {GREEN if summary['emergence_velocity'] > 0 else RED}{summary['emergence_velocity']:.1f}{RESET} (mols/1k f)")
        print(f"  Z-Stability:     {GREEN if summary['z_stability_avg'] > 0.5 else RED}{summary['z_stability_avg']:.2f}{RESET}")
        print(f"  Energy Vol:      {YELLOW if summary['energy_volatility'] > 0.1 else GREEN}{summary['energy_volatility']:.2f}{RESET}")
        print("-" * 50)
        print(f"  {BOLD}Top Molecules:{RESET}")
        for formula, count in summary['top_formed'][:3]:
            print(f"    - {formula:10s} : {count} times")
        print("="*50)

if __name__ == "__main__":
    import traceback
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--mode", choices=["audit", "forensic", "tune", "bench"], default="audit")
        parser.add_argument("--particles", type=int, default=3000)
        args = parser.parse_args()
        
        monitor = LifeMonitor(mode=args.mode)
        if args.particles: monitor.particles = args.particles
        monitor.run()
    except Exception as e:
        print(f"\n{RED}{BOLD}❌ CRITICAL ERROR IN LIFEMONITOR:{RESET}")
        print(f"{RED}{str(e)}{RESET}")
        traceback.print_exc()
        sys.exit(1)
