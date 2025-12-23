"""
Profile Bottleneck - Análisis detallado de cuellos de botella
================================================================
"""
import sys
import os

# Fix path - go to project root
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

import time
import numpy as np

# Usar Vulkan como la app principal
import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)

from src.systems.taichi_fields import (
    n_particles, pos, pos_z, vel, vel_z, atom_types, num_enlaces, enlaces_idx,
    molecule_id, is_active, total_bonds_count, radii, manos_libres,
    MASAS_ATOMICAS
)
from src.systems.simulation_gpu import simulation_step_gpu, init_molecule_ids
from src.config import system_constants as cfg

# Colores
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def setup_simulation(n_parts: int):
    """Inicializa la simulación con n_parts partículas."""
    from src.systems.taichi_fields import (
        grid_count, n_simulated_chemistry, n_simulated_physics,
        temperature, prob_enlace_base, dist_equilibrio, spring_k, damping,
        dist_rotura, max_fuerza, rango_enlace_max, sim_bounds
    )
    
    n_particles[None] = n_parts
    temperature[None] = 0.5
    prob_enlace_base[None] = 0.15
    dist_equilibrio[None] = 80.0
    spring_k[None] = 0.002
    damping[None] = 0.0004
    dist_rotura[None] = 150.0
    max_fuerza[None] = 80.0
    rango_enlace_max[None] = 120.0
    
    # Posiciones aleatorias
    center = cfg.WORLD_SIZE / 2
    pos_np = (np.random.rand(cfg.MAX_PARTICLES, 2).astype(np.float32) - 0.5) * 600 + center
    pos.from_numpy(pos_np)
    
    posZ_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.float32)
    pos_z.from_numpy(posZ_np)
    
    vel_np = np.zeros((cfg.MAX_PARTICLES, 2), dtype=np.float32)
    vel.from_numpy(vel_np)
    vel_z.from_numpy(posZ_np.copy())
    
    # Tipos y radios
    types_np = np.random.choice(6, size=cfg.MAX_PARTICLES).astype(np.int32)
    atom_types.from_numpy(types_np)
    
    radii_np = np.array([MASAS_ATOMICAS[types_np[i]] * 3 + 8 for i in range(cfg.MAX_PARTICLES)], dtype=np.float32)
    radii.from_numpy(radii_np)
    
    manos_np = np.array([2.0 if types_np[i] != 1 else 1.0 for i in range(cfg.MAX_PARTICLES)], dtype=np.float32)
    manos_libres.from_numpy(manos_np)
    
    # Active
    active_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.int32)
    active_np[:n_parts] = 1
    is_active.from_numpy(active_np)
    
    # Bounds
    sim_bounds[0] = 0
    sim_bounds[1] = cfg.WORLD_SIZE
    sim_bounds[2] = 0
    sim_bounds[3] = cfg.WORLD_SIZE
    
    # Init molecules
    init_molecule_ids()
    ti.sync()


def profile_subsystems(n_particles_test: int, n_frames: int):
    """Mide tiempos por subsistema."""
    setup_simulation(n_particles_test)
    
    # Warm up
    for _ in range(10):
        simulation_step_gpu(1)
    ti.sync()
    
    # Ahora medir con mayor granularidad
    from src.systems.physics_kernels import (
        physics_pre_step, physics_post_step, resolve_constraints_grid
    )
    from src.systems.chemistry.bonding import check_bonding_gpu, reset_molecule_ids, propagate_molecule_ids_step
    from src.systems.chemistry.bond_forces import apply_bond_forces_gpu
    from src.systems.chemistry.vsepr import apply_vsepr_geometry_gpu
    from src.systems.chemistry.dihedral import apply_dihedral_forces_gpu
    from src.systems.simulation_gpu import update_grid
    
    times = {
        'grid': [],
        'physics_pre': [],
        'constraints': [],
        'physics_post': [],
        'bonding': [],
        'bond_forces': [],
        'vsepr': [],
        'dihedral': [],
        'mol_propagate': [],
        'sync': [],
        'TOTAL_SIM_STEP': [],
    }
    
    for frame in range(n_frames):
        # TOTAL simulation step
        t_total_start = time.perf_counter()
        
        # Grid
        t0 = time.perf_counter()
        update_grid()
        ti.sync()
        times['grid'].append((time.perf_counter() - t0) * 1000)
        
        # Physics Pre
        t0 = time.perf_counter()
        physics_pre_step()
        ti.sync()
        times['physics_pre'].append((time.perf_counter() - t0) * 1000)
        
        # Constraints (collisions)
        t0 = time.perf_counter()
        resolve_constraints_grid()
        ti.sync()
        times['constraints'].append((time.perf_counter() - t0) * 1000)
        
        # Bond Forces
        t0 = time.perf_counter()
        apply_bond_forces_gpu()
        ti.sync()
        times['bond_forces'].append((time.perf_counter() - t0) * 1000)
        
        # VSEPR
        t0 = time.perf_counter()
        apply_vsepr_geometry_gpu()
        ti.sync()
        times['vsepr'].append((time.perf_counter() - t0) * 1000)
        
        # Dihedral
        t0 = time.perf_counter()
        apply_dihedral_forces_gpu()
        ti.sync()
        times['dihedral'].append((time.perf_counter() - t0) * 1000)
        
        # Physics Post
        t0 = time.perf_counter()
        physics_post_step(1.0, 1)
        ti.sync()
        times['physics_post'].append((time.perf_counter() - t0) * 1000)
        
        # Bonding (cada 5 frames)
        if frame % 5 == 0:
            t0 = time.perf_counter()
            check_bonding_gpu()
            ti.sync()
            times['bonding'].append((time.perf_counter() - t0) * 1000)
        
        # Molecule propagation (cada 20 frames)
        if frame % 20 == 0:
            t0 = time.perf_counter()
            reset_molecule_ids()
            for _ in range(5):
                propagate_molecule_ids_step()
            ti.sync()
            times['mol_propagate'].append((time.perf_counter() - t0) * 1000)
        
        # Sync final
        t0 = time.perf_counter()
        ti.sync()
        times['sync'].append((time.perf_counter() - t0) * 1000)
        
        times['TOTAL_SIM_STEP'].append((time.perf_counter() - t_total_start) * 1000)
    
    return times


def print_results(times: dict, n_particles: int, n_frames: int):
    """Imprime resultados ordenados por impacto."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}⏱️  PROFILE RESULTS - {n_particles} particles, {n_frames} frames{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")
    
    # Calcular promedios
    averages = {}
    for key, values in times.items():
        if values:
            averages[key] = np.mean(values)
        else:
            averages[key] = 0.0
    
    # Ordenar por tiempo (descendente)
    sorted_keys = sorted(averages.keys(), key=lambda k: averages[k], reverse=True)
    
    total_sim = averages.get('TOTAL_SIM_STEP', 1.0)
    
    print(f"{'Subsistema':<20} {'Tiempo Avg':<12} {'% del Total':<12} {'Impacto':<10}")
    print("-" * 54)
    
    for key in sorted_keys:
        avg = averages[key]
        pct = (avg / total_sim) * 100 if total_sim > 0 else 0
        
        # Color por impacto
        if pct > 30:
            color = RED
            impact = "🔴 CRÍTICO"
        elif pct > 15:
            color = YELLOW
            impact = "🟡 ALTO"
        elif pct > 5:
            color = CYAN
            impact = "🔵 MEDIO"
        else:
            color = GREEN
            impact = "🟢 BAJO"
        
        print(f"{color}{key:<20} {avg:>8.3f} ms   {pct:>8.1f}%    {impact}{RESET}")
    
    print("-" * 54)
    
    # Estimación FPS
    frame_time_ms = averages.get('TOTAL_SIM_STEP', 16.67)
    estimated_fps = 1000.0 / frame_time_ms if frame_time_ms > 0 else 0
    
    print(f"\n{BOLD}Frame Time Avg: {frame_time_ms:.2f} ms → {GREEN}{estimated_fps:.1f} FPS estimado (solo sim){RESET}")
    print(f"{BOLD}Bonds Formados: {total_bonds_count[None]}{RESET}")
    
    # Recomendaciones
    print(f"\n{BOLD}{YELLOW}💡 RECOMENDACIONES:{RESET}")
    
    bottleneck = sorted_keys[0]
    if bottleneck == 'constraints':
        print(f"  - El sistema de {RED}COLISIONES{RESET} es el cuello de botella")
        print(f"  - Posible optimización: Reducir SOLVER_ITERATIONS o usar broadphase más agresivo")
    elif bottleneck == 'vsepr':
        print(f"  - El sistema de {RED}VSEPR{RESET} es el cuello de botella")
        print(f"  - Posible optimización: Ejecutar VSEPR menos frecuentemente o simplificar cálculos")
    elif bottleneck == 'dihedral':
        print(f"  - El sistema de {RED}DIHEDRAL{RESET} es el cuello de botella")
        print(f"  - Posible optimización: Skip dihedral cuando num_enlaces < 2")
    elif bottleneck == 'sync':
        print(f"  - La {RED}SINCRONIZACIÓN GPU{RESET} es el cuello de botella")
        print(f"  - Posible optimización: Reducir ti.sync() calls")
    elif bottleneck == 'bonding':
        print(f"  - El sistema de {RED}BONDING{RESET} es el cuello de botella")
        print(f"  - Posible optimización: Ejecutar cada 10 frames en vez de 5")
    else:
        print(f"  - El cuello de botella es: {RED}{bottleneck}{RESET}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--particles", type=int, default=5000)
    parser.add_argument("--frames", type=int, default=100)
    args = parser.parse_args()
    
    print(f"{BOLD}{CYAN}🔬 LifeSimulator Bottleneck Profiler{RESET}")
    print(f"Testing with {args.particles} particles for {args.frames} frames...")
    
    times = profile_subsystems(args.particles, args.frames)
    print_results(times, args.particles, args.frames)
