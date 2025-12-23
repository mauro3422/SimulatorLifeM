"""
Advanced Molecular Analyzer & Benchmark
=======================================
Runs a controlled simulation to benchmark molecular stability,
VSEPR geometry accuracy, and chemical realism.
Generates a 'chemical_health_report.md'.
"""
import sys
import os
import time
import numpy as np
from collections import Counter, defaultdict

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)

from src.systems.taichi_fields import (
    n_particles, pos, vel, pos_old, is_active, atom_types, pos_z,
    num_enlaces, enlaces_idx, molecule_id, manos_libres,
    partial_charge, prob_enlace_base, rango_enlace_max,
    VALENCIAS_MAX, VALENCIA_ELECTRONES, AFINIDAD_MATRIX, MASAS_ATOMICAS,
    medium_polarity, temperature, sim_bounds, ELECTRONEG,
    gravity, friction, max_speed, dist_rotura, dist_equilibrio, spring_k,
    total_bonds_count, next_molecule_id, needs_propagate,
    world_width, world_height, damping, radii, total_bonds_broken_dist
)
from src.systems.simulation_gpu import (
    kernel_pre_step_fused, kernel_resolve_constraints, 
    kernel_post_step_fused, kernel_bonding, update_partial_charges,
    reset_molecule_ids, propagate_molecule_ids_step, init_molecule_ids
)
from src.systems.molecular_analyzer import get_molecular_analyzer
from src.config import system_constants as sys_cfg
from src.config.molecules import get_molecule_name

# Configuration for Benchmark
TARGET_PARTICLES = 3000
FRAMES_TO_RUN = 3000
SPAWN_AREA = 600.0
WORLD_CENTER = sys_cfg.WORLD_SIZE / 2.0
REPORT_FILE = "chemical_health_report.md"

def get_molecule_name(formula: str) -> str:
    """Helper to get common names for formulas."""
    names = {
        "H2O1": "Agua",
        "C1H4": "Metano",
        "N1H3": "Amoníaco",
        "C1O2": "Dióxido de Carbono",
        "O2": "Oxígeno molecular",
        "H2": "Hidrógeno molecular",
        "N2": "Nitrógeno molecular",
        "C1H3": "Metilo",
        "H1O1": "Hidroxilo",
        "N1O1": "Óxido Nítrico",
        "C1N1": "Cianuro",
        "C2H6": "Etano",
        "C2H4": "Eteno"
    }
    return names.get(formula, "Desconocida")

def init_simulation_gpu(p_count: int):
    """Inicialización directa para evitar problemas de sincronización en scripts."""
    n_particles[None] = p_count
    # Safely set bounds using from_numpy (Python scope)
    bounds_np = np.array([0.0, 0.0, float(sys_cfg.WORLD_SIZE), float(sys_cfg.WORLD_SIZE)], dtype=np.float32)
    sim_bounds.from_numpy(bounds_np)
    
    # Física
    gravity[None] = 0.0
    friction[None] = 0.95
    max_speed[None] = 50.0
    dist_rotura[None] = 300.0
    dist_equilibrio[None] = 60.0
    spring_k[None] = 0.1
    damping[None] = 0.1
    world_width[None] = float(sys_cfg.WORLD_SIZE)
    world_height[None] = float(sys_cfg.WORLD_SIZE)
    
    # Química
    prob_enlace_base[None] = 1.0 # Max for benchmark
    rango_enlace_max[None] = 300.0 # Increased from 210
    medium_polarity[None] = 0.8
    temperature[None] = 5.0
    
    # Reset
    total_bonds_count[None] = 0
    total_bonds_broken_dist[None] = 0
    next_molecule_id[None] = 1

def init_benchmark():
    """Initializes the simulation for benchmarking."""
    print(f"🔬 Initializing Benchmark with {TARGET_PARTICLES} particles...")
    
    init_simulation_gpu(TARGET_PARTICLES)
    
    # Atomic Properties (C, H, N, O, P, S)
    MASAS_ATOMICAS.from_numpy(np.array([12.0, 1.0, 14.0, 16.0, 31.0, 32.0], dtype=np.float32))
    ELECTRONEG.from_numpy(np.array([2.55, 2.20, 3.04, 3.44, 2.19, 2.58], dtype=np.float32))
    VALENCIAS_MAX.from_numpy(np.array([4, 1, 3, 2, 5, 6], dtype=np.int32))
    VALENCIA_ELECTRONES.from_numpy(np.array([4, 1, 5, 6, 5, 6], dtype=np.int32))

    # Affinities
    aff_np = np.ones((6, 6), dtype=np.float32)
    # Index 1 is Hydrogen, Index 3 is Oxygen
    aff_np[1, 3] = 2.0 # H-O
    aff_np[3, 1] = 2.0 # O-H
    AFINIDAD_MATRIX.from_numpy(aff_np)
    
    # [C, H, N, O, P, S]
    types_np = np.random.choice(
        [0, 1, 2, 3, 4, 5],
        size=sys_cfg.MAX_PARTICLES,
        p=[0.15, 0.50, 0.05, 0.25, 0.025, 0.025]
    ).astype(np.int32)
    atom_types.from_numpy(types_np)
    
    # Initial Positions
    pos_np = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:TARGET_PARTICLES] = (
        np.random.rand(TARGET_PARTICLES, 2) * SPAWN_AREA 
        + (WORLD_CENTER - SPAWN_AREA / 2.0)
    )
    print(f"[DEBUG] pos_np range: {pos_np[:TARGET_PARTICLES].min(axis=0)} to {pos_np[:TARGET_PARTICLES].max(axis=0)}")
    pos.from_numpy(pos_np)
    ti.sync()
    print(f"[DEBUG] pos range after from_numpy: {pos.to_numpy()[:TARGET_PARTICLES].min(axis=0)} to {pos.to_numpy()[:TARGET_PARTICLES].max(axis=0)}")
    pos_old.from_numpy(pos_np)
    pos_z.fill(0.0)
    
    # Radii
    radii_vals = np.array([10.0, 6.0, 9.0, 8.0, 11.0, 12.0], dtype=np.float32) * 1.5 # Adjusted scale
    radii_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    for i in range(TARGET_PARTICLES):
        radii_np[i] = radii_vals[types_np[i]]
    radii.from_numpy(radii_np)
    
    active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    active_np[:TARGET_PARTICLES] = 1
    is_active.from_numpy(active_np)
    
    # Manos Libres
    v_max = [4, 1, 3, 2, 5, 6]
    manos_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    for i in range(TARGET_PARTICLES):
        manos_np[i] = float(v_max[types_np[i]])
    manos_libres.from_numpy(manos_np)

    num_enlaces.fill(0)
    enlaces_idx.fill(-1)
    molecule_id.fill(0)
    init_molecule_ids()
    
    ti.sync()
    print("✅ Benchmark Ready")
    return types_np

def init_prebiotic_soup():
    """Initializes a high-density environment to force complex reactions."""
    print(f"🧬 Initializing Prebiotic Soup Stress Test...")
    init_simulation_gpu(5000) # More particles
    
    # [C, H, N, O, P, S] - Higher Carbon/Nitrogen for complexity
    types_np = np.random.choice(
        [0, 1, 2, 3, 4, 5],
        size=sys_cfg.MAX_PARTICLES,
        p=[0.30, 0.40, 0.10, 0.15, 0.025, 0.025]
    ).astype(np.int32)
    atom_types.from_numpy(types_np)
    
    # High density spawning
    pos_np = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:5000] = (
        np.random.rand(5000, 2) * 400.0 # Very tight area
        + (WORLD_CENTER - 200.0)
    )
    pos.from_numpy(pos_np)
    pos_old.from_numpy(pos_np)
    
    # High temperature and reactivity
    temperature[None] = 15.0 # Hot soup
    prob_enlace_base[None] = 1.0
    rango_enlace_max[None] = 300.0
    
    active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    active_np[:5000] = 1
    is_active.from_numpy(active_np)
    
    num_enlaces.fill(0)
    enlaces_idx.fill(-1)
    molecule_id.fill(0)
    init_molecule_ids()
    ti.sync()
    return types_np

def run_benchmark(frames: int = None):
    """Ejecuta el benchmark de simulación química."""
    global FRAMES_TO_RUN
    if frames is not None:
        FRAMES_TO_RUN = frames
    print(f"🚀 Iniciando benchmark con {FRAMES_TO_RUN} frames...")
    
    # Initialization
    init_benchmark()
    
    print(f"⏱️ Running {FRAMES_TO_RUN} frames...")
    start_time = time.time()
    
    # Reset statistics
    analyzer = get_molecular_analyzer()
    analyzer.reset() # This needs implementation in analyzer
    
    # Statistics accumulation
    stability_stats = [] # frame -> bond_count
    
    from src.systems.taichi_fields import (
        debug_particles_checked, debug_neighbors_found, 
        debug_distance_passed, debug_prob_passed,
        total_bonds_count
    )

    for frame in range(1, FRAMES_TO_RUN + 1):
        if frame == 1:
            debug_particles_checked[None] = 0
            debug_neighbors_found[None] = 0
            debug_distance_passed[None] = 0
            debug_prob_passed[None] = 0

        # Simulation step
        update_partial_charges()
        kernel_pre_step_fused()
        
        # Solver iterations for stability
        for _ in range(5):
            kernel_resolve_constraints()
            
        # t_total = 5.0 + temperature[None] # Original line, now fixed to 10.0
        kernel_post_step_fused(10.0, 0) # Fixed temperature and no alternating
        
        # Chemistry and IDs
        kernel_bonding()
        
        # Propagate IDs (like main.py)
        reset_molecule_ids()
        for _ in range(10): # Trace molecules
            propagate_molecule_ids_step()
        
        # Check every single frame to catch the culprit
        ti.sync()
        p0 = pos[0].x
        if p0 < 0.1 or np.isnan(p0):
            print(f"❌ CRITICAL COLLAPSE at frame {frame}!")
            print(f"   Pos[0]: {pos[0]}, OldPos[0]: {pos_old[0]}, Vel[0]: {vel[0]}")
            print(f"   IsActive[0]: {is_active[0]}, Val[0]: {num_enlaces[0]}, Manos[0]: {manos_libres[0]}")
            print(f"   Radii[0]: {radii[0]}")
            print(f"   World: {world_width[None]}x{world_height[None]}, Bounds: {sim_bounds.to_numpy()}")
            break

        # Analyze and store stats every 50 frames
        if frame % 50 == 0:
            ti.sync()
            current_bonds = total_bonds_count[None]
            stability_stats.append(current_bonds)
            
            p_numpy = pos.to_numpy()[:TARGET_PARTICLES]
            p_min = p_numpy.min(axis=0)
            p_max = p_numpy.max(axis=0)
            
            if p_max[0] < 1.0:
                print(f"❌ CRITICAL FAILURE at frame {frame}: Particles lost!")
                print(f"   n_particles: {n_particles[None]}")
                print(f"   sim_bounds: {sim_bounds.to_numpy()}")
                print(f"   is_active sum: {is_active.to_numpy()[:TARGET_PARTICLES].sum()}")
                break

            if frame % 500 == 0:
                ti.sync()
                pos_cur = p_numpy
                manos_cur = manos_libres.to_numpy()[:TARGET_PARTICLES]
                print(f"   Frame {frame}: Bonds={current_bonds}")
                print(f"     [DEBUG] Checked: {debug_particles_checked[None]}, Neighbors: {debug_neighbors_found[None]}, DistPassed: {debug_distance_passed[None]}, ProbPassed: {debug_prob_passed[None]}")
                print(f"     [STATE] PosRange: {pos_cur.min(axis=0)} to {pos_cur.max(axis=0)}")
                print(f"     [STATE] Manos Sum: {manos_cur.sum():.1f}, Active: {(manos_cur > 0.5).sum()}")
                print(f"     [GLOBAL] n_particles: {n_particles[None]}, Bounds: {sim_bounds.to_numpy()}")
                
            pos_np = pos.to_numpy()
            pos_z_np = pos_z.to_numpy()
            atom_types_np = atom_types.to_numpy()
            enlaces_idx_np = enlaces_idx.to_numpy()
            num_enlaces_np = num_enlaces.to_numpy()
            molecule_id_np = molecule_id.to_numpy()
            is_active_np = is_active.to_numpy()
            
            analysis = analyzer.analyze_frame(
                pos_np, pos_z_np, atom_types_np, 
                enlaces_idx_np, num_enlaces_np, 
                molecule_id_np, is_active_np
            )
            
            # Print recent events to console during benchmark for live audit
            if analysis['formations']:
                for f in analysis['formations']:
                    print(f"   ✨ Formed: {f} ({get_molecule_name(f)})")
            if analysis['destructions']:
                for d in analysis['destructions']:
                    # print(f"   💥 Broken: {d}")
                    pass

    total_time = time.time() - start_time
    print(f"🏁 Benchmark Finished in {total_time:.2f}s")
    
    generate_report(analyzer, stability_stats, total_time)

def generate_report(analyzer, stability_stats, total_time):
    """Generates the Markdown report."""
    summary = analyzer.get_summary()
    
    report = f"""# 🧪 Chemical Health & Geometry Report
**Generated on**: {time.ctime()}
**Benchmark Time**: {total_time:.2f}s for {FRAMES_TO_RUN} frames

## 1. Stability Overview
- **Initial Bonds**: {stability_stats[0]}
- **Final Bonds**: {stability_stats[-1]}
- **Persistence Rate**: {((stability_stats[-1] / stability_stats[0]) * 100) if stability_stats[0] > 0 else 0:.1f}%
- **Max Molecule Size**: {max([len(s.formula)//2 + 1 for s in analyzer.formula_stats.values()] + [0])} atoms

## 2. VSEPR Geometry Validation
| Molecule | Common Name | Avg Measured Angle | Target Angle | Error (%) |
|----------|-------------|--------------------|--------------|-----------|
"""
    
    # Ideal angles lookup
    ideals = {
        "H2O1": 104.5,
        "C1H4": 109.5,
        "N1H3": 107.0,
        "C1O2": 180.0,
        "O2": 180.0,
        "H2": 180.0,
    }
    
    for formula, ideal in ideals.items():
        samples = analyzer.angle_samples[formula]
        if samples:
            avg = np.mean(samples)
            error = abs(avg - ideal) / ideal * 100
            report += f"| {formula} | {get_molecule_name(formula)} | {avg:.2f}° | {ideal}° | {error:.1f}% |\n"

    report += """
List of discovered molecules and their perceived stability.

| Formula | Name | Freq | Avg Lifetime (f) | Status |
|---------|------|------|------------------|--------|
"""
    
    sorted_stats = sorted(analyzer.formula_stats.values(), key=lambda s: s.times_formed, reverse=True)
    for s in sorted_stats[:15]:
        name = get_molecule_name(s.formula)
        status = "✅ Known" if name != "Desconocida" else "❓ Unknown"
        report += f"| {s.formula} | {name} | {s.times_formed} | {s.avg_lifetime:.1f} | {status} |\n"

    report += """
---
*This report was automatically generated by the Advanced Molecular Analyzer.*
"""
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"📝 Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    run_benchmark()
