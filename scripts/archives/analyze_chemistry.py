"""
Chemistry Analysis Script - Análisis de Química de Simulación
==============================================================
Script standalone para verificar la formación de moléculas,
ángulos de enlace y estabilidad química.

Ejecutar: python scripts/analyze_chemistry.py
"""

import sys
import os
import numpy as np
from collections import defaultdict

# Path setup
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Initialize Taichi FIRST
import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)
print("[GPU] Taichi inicializado con Vulkan")

# Now import fields and kernels
from src.systems.taichi_fields import (
    n_particles, pos, vel, is_active, atom_types,
    manos_libres, num_enlaces, enlaces_idx, molecule_id,
    total_bonds_count, prob_enlace_base, rango_enlace_max,
    grid_count, VALENCIAS_MAX, AFINIDAD_MATRIX,
    world_width, world_height, gravity, friction, temperature,
    max_speed, dist_equilibrio, spring_k, damping,
    dist_rotura, max_fuerza
)
from src.config import system_constants as sys_cfg
from src.systems.simulation_gpu import (
    kernel_pre_step_fused, kernel_bonding, kernel_resolve_constraints,
    kernel_post_step_fused, simulation_step_gpu, run_simulation_fast
)
from src.config.molecules import get_molecule_name

ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']
VALENCIAS = [4, 1, 3, 2, 5, 2]  # C, H, N, O, P, S


def initialize_simulation(n_part: int = 1000, spawn_area: float = 800.0):
    """Inicializa la simulación con partículas."""
    print(f"\n[INIT] Configurando {n_part} partículas en área {spawn_area}x{spawn_area}...")
    
    # Set particle count
    n_particles[None] = n_part
    
    # Spawn positions in cluster
    center = sys_cfg.WORLD_SIZE / 2.0
    pos_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_data[:n_part] = (np.random.rand(n_part, 2) * spawn_area) + (center - spawn_area / 2.0)
    pos.from_numpy(pos_data)
    
    # Random velocities
    vel_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    vel_data[:n_part] = (np.random.rand(n_part, 2) - 0.5) * 20.0
    vel.from_numpy(vel_data)
    
    # All active
    is_active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    is_active_np[:n_part] = 1
    is_active.from_numpy(is_active_np)
    
    # Random atom types with realistic distribution
    # H=50%, C=20%, O=15%, N=10%, S=3%, P=2%
    probs = [0.20, 0.50, 0.10, 0.15, 0.02, 0.03]  # C, H, N, O, P, S
    atom_types_data = np.random.choice(6, size=sys_cfg.MAX_PARTICLES, p=probs).astype(np.int32)
    atom_types.from_numpy(atom_types_data)
    
    # Set manos_libres based on valence
    manos_data = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    for i in range(n_part):
        t = atom_types_data[i]
        manos_data[i] = float(VALENCIAS[t])
    manos_libres.from_numpy(manos_data)
    
    # Initialize molecule IDs (each atom is its own molecule initially)
    mol_id_data = np.arange(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    molecule_id.from_numpy(mol_id_data)
    
    # Reset bonds
    num_enlaces.fill(0)
    enlaces_idx.fill(-1)
    total_bonds_count[None] = 0
    
    # Physics parameters
    world_width[None] = sys_cfg.WORLD_SIZE
    world_height[None] = sys_cfg.WORLD_SIZE
    gravity[None] = 0.0
    friction[None] = 0.95
    temperature[None] = 0.1
    max_speed[None] = sys_cfg.MAX_SPEED
    
    # Bond parameters
    prob_enlace_base[None] = 0.3
    rango_enlace_max[None] = 210.0
    dist_equilibrio[None] = sys_cfg.DIST_EQUILIBRIO
    spring_k[None] = 0.5
    damping[None] = 0.8
    dist_rotura[None] = sys_cfg.DIST_ROTURA
    max_fuerza[None] = sys_cfg.MAX_FORCE
    
    print(f"[INIT] ✅ Partículas inicializadas")
    return n_part


def run_simulation_frames(n_frames: int = 100, report_interval: int = 20):
    """Ejecuta N frames de simulación y reporta progreso."""
    print(f"\n[SIM] Ejecutando {n_frames} frames de simulación...")
    
    bonds_over_time = []
    
    for frame in range(n_frames):
        # Run one simulation step
        simulation_step_gpu(1)
        ti.sync()
        
        if frame % report_interval == 0 or frame == n_frames - 1:
            bonds = total_bonds_count[None]
            bonds_over_time.append((frame, bonds))
            print(f"   Frame {frame:4d}: {bonds} enlaces")
    
    return bonds_over_time


def analyze_final_state(n_part: int):
    """Analiza el estado final de la simulación."""
    print("\n" + "="*60)
    print("📊 ANÁLISIS FINAL DE QUÍMICA")
    print("="*60)
    
    # Get data from GPU
    num_enlaces_np = num_enlaces.to_numpy()[:n_part]
    atom_types_np = atom_types.to_numpy()[:n_part]
    enlaces_idx_np = enlaces_idx.to_numpy()[:n_part]
    is_active_np = is_active.to_numpy()[:n_part]
    mol_ids_np = molecule_id.to_numpy()[:n_part]
    pos_np = pos.to_numpy()[:n_part]
    
    # 1. Atom distribution
    print("\n🔬 DISTRIBUCIÓN DE ÁTOMOS Y ENLACES:")
    print("-" * 40)
    for t, sym in enumerate(ATOM_SYMBOLS):
        mask = atom_types_np == t
        count = np.sum(mask)
        if count > 0:
            avg_bonds = np.mean(num_enlaces_np[mask])
            max_val = VALENCIAS[t]
            violations = np.sum(num_enlaces_np[mask] > max_val)
            saturation = (avg_bonds / max_val) * 100 if max_val > 0 else 0
            print(f"   {sym}: {count:4d} átomos | avg enlaces: {avg_bonds:.2f}/{max_val} ({saturation:.0f}% sat) | violaciones: {violations}")
    
    # 2. Molecule detection
    print("\n🧬 MOLÉCULAS DETECTADAS:")
    print("-" * 40)
    mol_groups = defaultdict(list)
    for i in range(n_part):
        if is_active_np[i] and num_enlaces_np[i] > 0:
            mid = mol_ids_np[i]
            if mid >= 0:
                mol_groups[mid].append(i)
    
    formula_counts = defaultdict(int)
    formula_sizes = defaultdict(list)
    
    for mid, indices in mol_groups.items():
        if len(indices) >= 2:
            atom_counts = defaultdict(int)
            for idx in indices:
                t = atom_types_np[idx]
                if 0 <= t < len(ATOM_SYMBOLS):
                    atom_counts[ATOM_SYMBOLS[t]] += 1
            
            parts = []
            if 'C' in atom_counts: parts.append(f"C{atom_counts.pop('C')}")
            if 'H' in atom_counts: parts.append(f"H{atom_counts.pop('H')}")
            for s in sorted(atom_counts.keys()): 
                parts.append(f"{s}{atom_counts[s]}")
            formula = "".join(parts)
            formula_counts[formula] += 1
            formula_sizes[formula].append(len(indices))
    
    # Show top 15 formulas
    sorted_formulas = sorted(formula_counts.items(), key=lambda x: -x[1])[:15]
    known_count = 0
    unknown_count = 0
    
    for formula, count in sorted_formulas:
        name = get_molecule_name(formula)
        is_known = name != "Desconocida"
        status = "✅" if is_known else "❓"
        avg_size = np.mean(formula_sizes[formula])
        
        if is_known:
            known_count += count
            print(f"   {status} {formula:12s} x{count:3d} - {name}")
        else:
            unknown_count += count
            print(f"   {status} {formula:12s} x{count:3d} - Desconocida (avg size: {avg_size:.1f})")
    
    # 3. Angle analysis
    print("\n📐 ANÁLISIS DE ÁNGULOS DE ENLACE:")
    print("-" * 40)
    all_angles = []
    
    for i in range(n_part):
        n_bonds = num_enlaces_np[i]
        if n_bonds >= 2:
            p_center = pos_np[i]
            neighbors = []
            
            for b in range(n_bonds):
                j = enlaces_idx_np[i, b]
                if 0 <= j < n_part:
                    neighbors.append(j)
            
            # Calculate angles between pairs
            for a in range(len(neighbors)):
                for b in range(a + 1, len(neighbors)):
                    j1, j2 = neighbors[a], neighbors[b]
                    v1 = pos_np[j1] - p_center
                    v2 = pos_np[j2] - p_center
                    
                    len1 = np.linalg.norm(v1)
                    len2 = np.linalg.norm(v2)
                    
                    if len1 > 0.001 and len2 > 0.001:
                        cos_angle = np.clip(np.dot(v1, v2) / (len1 * len2), -1.0, 1.0)
                        angle_deg = np.degrees(np.arccos(cos_angle))
                        all_angles.append(angle_deg)
    
    if all_angles:
        angles_np = np.array(all_angles)
        print(f"   Total ángulos medidos: {len(angles_np)}")
        print(f"   Promedio: {np.mean(angles_np):.1f}°")
        print(f"   Desviación: {np.std(angles_np):.1f}°")
        print(f"   Rango: {np.min(angles_np):.1f}° - {np.max(angles_np):.1f}°")
        
        # Check VSEPR angles
        near_109 = np.sum((angles_np > 100) & (angles_np < 120))
        near_120 = np.sum((angles_np > 115) & (angles_np < 125))
        near_180 = np.sum(angles_np > 170)
        
        print(f"\n   Ángulos cerca de 109.5° (tetraédrico): {near_109}")
        print(f"   Ángulos cerca de 120° (trigonal): {near_120}")
        print(f"   Ángulos cerca de 180° (lineal): {near_180}")
    else:
        print("   No hay suficientes enlaces para medir ángulos")
    
    # 4. Valencia violations
    print("\n⚠️  VALIDACIÓN DE VALENCIA:")
    print("-" * 40)
    violations = 0
    violation_details = defaultdict(int)
    
    for i in range(n_part):
        if is_active_np[i]:
            t = atom_types_np[i]
            n_bonds = num_enlaces_np[i]
            if n_bonds > VALENCIAS[t]:
                violations += 1
                violation_details[(ATOM_SYMBOLS[t], n_bonds, VALENCIAS[t])] += 1
    
    if violations == 0:
        print("   ✅ No hay violaciones de valencia!")
    else:
        print(f"   ❌ Total violaciones: {violations}")
        for (sym, bonds, max_v), count in sorted(violation_details.items(), key=lambda x: -x[1])[:5]:
            print(f"      {sym} con {bonds} enlaces (max={max_v}): {count} casos")
    
    # 5. Summary
    print("\n" + "="*60)
    print("📋 RESUMEN")
    print("="*60)
    total_bonds = total_bonds_count[None]
    total_mols = len([g for g in mol_groups.values() if len(g) >= 2])
    
    print(f"   Total enlaces: {total_bonds}")
    print(f"   Moléculas formadas: {total_mols}")
    print(f"   Fórmulas únicas: {len(formula_counts)}")
    print(f"   Moléculas conocidas: {known_count}")
    print(f"   Moléculas desconocidas: {unknown_count}")
    print(f"   Violaciones valencia: {violations}")
    
    # Health check
    print("\n🏥 SALUD DEL SISTEMA:")
    if violations == 0:
        print("   ✅ Valencia: OK")
    else:
        print("   ⚠️  Valencia: Hay violaciones")
    
    if total_bonds > n_part * 0.3:
        print("   ✅ Formación de enlaces: Activa")
    else:
        print("   ⚠️  Formación de enlaces: Baja")
    
    if known_count > 0:
        print("   ✅ Moléculas conocidas: Detectadas")
    else:
        print("   ⚠️  Moléculas conocidas: Ninguna")


def main():
    print("\n" + "="*60)
    print("🔬 CHEMISTRY ANALYZER - LifeSimulator")
    print("="*60)
    
    # Initialize
    n_part = initialize_simulation(n_part=2000, spawn_area=600.0)
    
    # Run simulation
    bonds_history = run_simulation_frames(n_frames=150, report_interval=25)
    
    # Analyze
    analyze_final_state(n_part)
    
    print("\n" + "="*60)
    print("✅ Análisis completado")
    print("="*60)


if __name__ == "__main__":
    main()
