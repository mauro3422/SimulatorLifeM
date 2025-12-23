"""
Molecule Formation Diagnostic Script
=====================================
Runs the simulation and tracks what molecules are forming,
their frequencies, and identifies patterns or issues.
"""
import sys
import os
import time
import numpy as np
from collections import Counter, defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)

from src.systems.taichi_fields import (
    n_particles, pos, vel, is_active, atom_types, manos_libres,
    num_enlaces, enlaces_idx, total_bonds_count, temperature,
    grid_count, grid_pids, sim_bounds,
    VALENCIAS_MAX, VALENCIA_ELECTRONES, AFINIDAD_MATRIX, MASAS_ATOMICAS,
    medium_polarity
)
from src.systems.simulation_gpu import (
    kernel_pre_step_fused, kernel_bonding, 
    kernel_resolve_constraints, kernel_post_step_fused
)
from src.systems.physics_constants import BROWNIAN_K, BROWNIAN_BASE_TEMP
from src.config import system_constants as sys_cfg
from src.config.molecules import MOLECULES, get_molecule_name

# ============================================================
# CONFIGURATION
# ============================================================
TARGET_PARTICLES = 5000
FRAMES_TO_RUN = 2000  # Extended run for evolution analysis
REPORT_INTERVAL = 500  # Report every 500 frames
SPAWN_AREA = 500.0   # Tight cluster for more bonding
WORLD_CENTER = sys_cfg.WORLD_SIZE / 2.0

# Atom type mapping (ORDER MUST MATCH JSON LOADING: C, H, N, O, P, S)
ATOM_NAMES = ["C", "H", "N", "O", "P", "S"]  # Fixed order!
VALENCES = [4, 1, 3, 2, 5, 6]  # Chemical valences matching order

def init_particles():
    """Initialize particles in a tight cluster."""
    print(f"🔬 Initializing {TARGET_PARTICLES} particles...")
    
    n_particles[None] = TARGET_PARTICLES
    
    # Create position data - tight cluster
    pos_np = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[:TARGET_PARTICLES] = (
        np.random.rand(TARGET_PARTICLES, 2) * SPAWN_AREA 
        + (WORLD_CENTER - SPAWN_AREA / 2.0)
    )
    pos.from_numpy(pos_np)
    
    # Random atom types with REALISTIC distribution
    # Order: [C, H, N, O, P, S] (indices 0-5)
    # Realistic: H=45%, O=25%, C=20%, N=7%, P=1.5%, S=1.5%
    types_np = np.random.choice(
        [0, 1, 2, 3, 4, 5],
        size=sys_cfg.MAX_PARTICLES,
        p=[0.20, 0.45, 0.07, 0.25, 0.015, 0.015]
    ).astype(np.int32)
    atom_types.from_numpy(types_np)
    
    # Count distribution
    type_counts = Counter(types_np[:TARGET_PARTICLES])
    print("\n📊 Atom Distribution:")
    for t, name in enumerate(ATOM_NAMES):
        count = type_counts.get(t, 0)
        pct = count / TARGET_PARTICLES * 100
        print(f"  {name}: {count} ({pct:.1f}%)")
    
    # All particles active
    active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    active_np[:TARGET_PARTICLES] = 1
    is_active.from_numpy(active_np)
    
    # Initialize manos_libres based on valence
    manos_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    for i in range(TARGET_PARTICLES):
        t = types_np[i]
        manos_np[i] = float(VALENCES[t])
    manos_libres.from_numpy(manos_np)
    
    # Initialize velocities with thermal distribution (like main.py)
    # v_rms = sqrt(k * T / m)
    t_total = BROWNIAN_BASE_TEMP + 0.0  # Base temperature
    vel_np = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    masses = np.array([4.0, 1.0, 3.0, 2.0, 5.0, 6.0], dtype=np.float32)  # C,H,N,O,P,S
    for i in range(TARGET_PARTICLES):
        t = types_np[i]
        mass = masses[t]
        v_rms = np.sqrt(BROWNIAN_K * t_total / mass)
        # Random direction and magnitude
        angle = np.random.random() * 2 * np.pi
        mag = v_rms * np.random.random()
        vel_np[i, 0] = np.cos(angle) * mag
        vel_np[i, 1] = np.sin(angle) * mag
    vel.from_numpy(vel_np)
    
    # Set temperature
    temperature[None] = 0.0  # Uses BROWNIAN_BASE_TEMP internally
    
    # Reset bonds
    num_enlaces.fill(0)
    enlaces_idx.fill(-1)
    total_bonds_count[None] = 0
    
    # Set world bounds (no culling)
    sim_bounds[0] = 0.0
    sim_bounds[1] = 0.0
    sim_bounds[2] = sys_cfg.WORLD_SIZE
    sim_bounds[3] = sys_cfg.WORLD_SIZE
    
    # Set bonding parameters
    from src.systems.taichi_fields import prob_enlace_base, rango_enlace_max
    prob_enlace_base[None] = 0.3  # 30% base probability
    rango_enlace_max[None] = 210.0
    
    # Set valencias and valence electrons
    VALENCIAS_MAX.from_numpy(np.array(VALENCES, dtype=np.int32))
    v_electrons = np.array([4, 1, 5, 6, 5, 6], dtype=np.int32) # C, H, N, O, P, S
    VALENCIA_ELECTRONES.from_numpy(v_electrons)
    
    # Set affinities
    aff_np = np.ones((6, 6), dtype=np.float32)
    # H-O high affinity (for water)
    aff_np[0, 3] = 2.0  # H -> O
    aff_np[3, 0] = 2.0  # O -> H
    # C-H, C-O high (organics)
    aff_np[1, 0] = 1.5  # C -> H
    aff_np[0, 1] = 1.5  # H -> C
    aff_np[1, 3] = 1.8  # C -> O
    aff_np[3, 1] = 1.8  # O -> C
    AFINIDAD_MATRIX.from_numpy(aff_np)
    medium_polarity[None] = 0.8  # Simular AGUA para efecto hidrofóbico
    
    print(f"✅ Particles initialized")
    return types_np[:TARGET_PARTICLES]

def analyze_molecules(types_np):
    """Analyze current molecular composition."""
    enlaces_np = enlaces_idx.to_numpy()
    num_enlaces_np = num_enlaces.to_numpy()
    
    visited = set()
    molecules = []
    
    for i in range(TARGET_PARTICLES):
        if i in visited:
            continue
        
        # BFS to find connected component
        component = {i}
        queue = [i]
        
        while queue:
            curr = queue.pop(0)
            n_bonds = num_enlaces_np[curr]
            for k in range(n_bonds):
                neighbor = enlaces_np[curr, k]
                if neighbor >= 0 and neighbor not in component:
                    component.add(neighbor)
                    queue.append(neighbor)
        
        visited.update(component)
        
        if len(component) > 1:  # Only count molecules, not single atoms
            # Build formula
            counts = Counter()
            for idx in component:
                t = types_np[idx]
                counts[ATOM_NAMES[t]] += 1
            
            # Normalize formula (alphabetical order)
            formula = ""
            for sym in sorted(counts.keys()):
                formula += f"{sym}{counts[sym]}"
            
            molecules.append({
                'formula': formula,
                'size': len(component),
                'composition': dict(counts)
            })
    
    return molecules

def run_diagnostic():
    """Main diagnostic routine."""
    print("=" * 60)
    print("🧪 MOLECULE FORMATION DIAGNOSTIC")
    print("=" * 60)
    
    types_np = init_particles()
    
    # Initial bonding
    print("\n🔗 Running initial bonding...")
    kernel_pre_step_fused()
    ti.sync()
    kernel_bonding()
    ti.sync()
    
    initial_bonds = total_bonds_count[None]
    print(f"   Initial bonds formed: {initial_bonds}")
    
    # Run simulation
    print(f"\n⏱️ Running {FRAMES_TO_RUN} frames (reporting every {REPORT_INTERVAL})...")
    
    molecule_history = []
    last_bonds = initial_bonds
    
    for frame in range(1, FRAMES_TO_RUN + 1):
        # Full physics step like main.py:
        # 1. Pre-step + Grid
        kernel_pre_step_fused()
        
        # 2. Constraints solver (collisions, bonds)
        for _ in range(5):  # SOLVER_ITERATIONS
            kernel_resolve_constraints()
        
        # 3. Post-step (brownian motion, advanced rules)
        t_total = BROWNIAN_BASE_TEMP + temperature[None]
        kernel_post_step_fused(t_total, 1 if frame % 2 == 0 else 0)
        
        # 4. Chemistry (bonding)
        kernel_bonding()
        
        if frame % REPORT_INTERVAL == 0:  # Report every REPORT_INTERVAL frames
            ti.sync()
            current_bonds = total_bonds_count[None]
            molecules = analyze_molecules(types_np)
            
            formula_counts = Counter(m['formula'] for m in molecules)
            size_counts = Counter(m['size'] for m in molecules)
            
            # Find known molecules
            known_molecules = {k: v for k, v in formula_counts.items() if get_molecule_name(k) != "Desconocida"}
            
            # Statistics
            max_size = max(size_counts.keys()) if size_counts else 0
            small_molecules = sum(c for s, c in size_counts.items() if s <= 10)
            mega_molecules = sum(c for s, c in size_counts.items() if s > 100)
            
            print(f"\n{'='*50}")
            print(f"📊 FRAME {frame}/{FRAMES_TO_RUN}")
            print(f"{'='*50}")
            print(f"   Total bonds: {current_bonds} (Δ{current_bonds - last_bonds:+d})")
            print(f"   Distinct molecules: {len(molecules)}")
            print(f"   Small (≤10 atoms): {small_molecules}")
            print(f"   Mega (>100 atoms): {mega_molecules}")
            print(f"   Max molecule size: {max_size}")
            
            # Known molecules summary
            print(f"\n   🧪 Known Molecules:")
            h2o_count = formula_counts.get("H2O1", 0)
            h2_count = formula_counts.get("H2", 0)
            o2_count = formula_counts.get("O2", 0)
            ch4_count = formula_counts.get("C1H4", 0)
            co2_count = formula_counts.get("C1O2", 0)
            nh3_count = formula_counts.get("N1H3", 0)
            print(f"      H₂O: {h2o_count} | H₂: {h2_count} | O₂: {o2_count}")
            print(f"      CH₄: {ch4_count} | CO₂: {co2_count} | NH₃: {nh3_count}")
            
            molecule_history.append({
                'frame': frame,
                'total_bonds': current_bonds,
                'molecules': len(molecules),
                'h2o': h2o_count,
                'small': small_molecules,
                'mega': mega_molecules,
                'max_size': max_size
            })
            
            last_bonds = current_bonds
    
    ti.sync()
    
    # Final analysis
    print("\n" + "=" * 60)
    print("📋 FINAL ANALYSIS")
    print("=" * 60)
    
    molecules = analyze_molecules(types_np)
    formula_counts = Counter(m['formula'] for m in molecules)
    
    print(f"\n🔬 Total distinct molecules: {len(molecules)}")
    print(f"🔗 Total bonds: {total_bonds_count[None]}")
    
    # Top formulas
    print("\n📈 TOP 20 MOLECULE TYPES:")
    print("-" * 40)
    for formula, count in formula_counts.most_common(20):
        name = get_molecule_name(formula)
        known = "✅" if name != "Desconocida" else "❓"
        print(f"  {known} {formula:15} x{count:4} - {name}")
    
    # Specific molecule checks
    print("\n🔍 SPECIFIC MOLECULE CHECK:")
    print("-" * 40)
    
    target_molecules = ["H2", "O2", "N2", "H2O1", "C1H4", "C1O2", "N1H3"]
    for target in target_molecules:
        count = formula_counts.get(target, 0)
        name = get_molecule_name(target)
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {target:8} ({name:20}): {count}")
    
    # Size distribution
    print("\n📐 MOLECULE SIZE DISTRIBUTION:")
    print("-" * 40)
    size_counts = Counter(m['size'] for m in molecules)
    for size in sorted(size_counts.keys())[:10]:
        count = size_counts[size]
        bar = "█" * min(count // 10, 40)
        print(f"  Size {size:2}: {count:4} {bar}")
    
    # Bond type analysis
    print("\n🧬 BOND TYPE ANALYSIS:")
    print("-" * 40)
    
    enlaces_np = enlaces_idx.to_numpy()
    num_enlaces_np = num_enlaces.to_numpy()
    
    bond_types = Counter()
    for i in range(TARGET_PARTICLES):
        t_i = ATOM_NAMES[types_np[i]]
        for k in range(num_enlaces_np[i]):
            j = enlaces_np[i, k]
            if j > i:  # Count each bond once
                t_j = ATOM_NAMES[types_np[j]]
                bond = tuple(sorted([t_i, t_j]))
                bond_types[bond] += 1
    
    print("  Bond Type    Count   % of Total")
    total_bonds = sum(bond_types.values())
    for bond, count in bond_types.most_common():
        pct = count / total_bonds * 100 if total_bonds > 0 else 0
        print(f"  {bond[0]}-{bond[1]:1}:        {count:5}   ({pct:5.1f}%)")
    
    # Chemistry insights
    print("\n💡 CHEMISTRY INSIGHTS:")
    print("-" * 40)
    
    h2o_count = formula_counts.get("H2O1", 0)
    h2_count = formula_counts.get("H2", 0)
    o2_count = formula_counts.get("O2", 0)
    
    if h2o_count == 0:
        h_h_bonds = bond_types.get(("H", "H"), 0)
        h_o_bonds = bond_types.get(("H", "O"), 0)
        o_o_bonds = bond_types.get(("O", "O"), 0)
        
        print(f"  ⚠️ No water (H2O) detected!")
        print(f"     H-H bonds: {h_h_bonds}")
        print(f"     H-O bonds: {h_o_bonds}")
        print(f"     O-O bonds: {o_o_bonds}")
        
        if h_h_bonds > h_o_bonds:
            print("     → H prefers bonding with H over O")
            print("     → Consider increasing H-O affinity")
        
        if o_o_bonds > 0:
            print("     → O is forming O2 instead of water")
    else:
        print(f"  ✅ Water detected: {h2o_count} molecules")
    
    print("\n" + "=" * 60)
    print("🏁 DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_diagnostic()
