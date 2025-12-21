"""
GPU-Accelerated Simulation Engine (Orquestador)
================================================
Orquesta los kernels de física y química para ejecutar
la simulación completa en GPU.

Los kernels están en:
- physics_kernels.py: Física básica, colisiones, Brownian, Coulomb
- chemistry_kernels.py: Enlaces, fuerzas de resorte, evolución
"""
import taichi as ti
import numpy as np
import src.config as cfg

# ===================================================================
# IMPORTS DE KERNELS
# ===================================================================

# Kernels de física
from src.systems.physics_kernels import (
    physics_pre_step,
    physics_post_step,
    resolve_constraints_grid,
    apply_brownian_motion_gpu,
    apply_coulomb_repulsion_gpu,
    shake_simulation
)

# Kernels de química
from src.systems.chemistry_kernels import (
    check_bonding_gpu,
    apply_bond_forces_gpu,
    apply_evolutionary_effects_gpu
)

# Campos Taichi
from src.systems.taichi_fields import (
    # Constantes
    MAX_PARTICLES, SOLVER_ITERATIONS, GRID_CELL_SIZE, GRID_RES,
    
    # Campos de partículas
    pos, vel, radii, is_active, atom_types, n_particles,
    pos_normalized, colors,
    
    # Campos de química
    manos_libres, enlaces_idx, num_enlaces,
    
    # Grid espacial
    grid_count, grid_pids, sim_bounds,
    visible_indices, n_visible,
    
    # Contadores
    active_particles_count, total_bonds_count,
    total_mutations, total_tunnels,
    
    # Parámetros
    gravity, friction, temperature, max_speed,
    world_width, world_height,
    dist_equilibrio, spring_k, damping,
    rango_enlace_min, rango_enlace_max, dist_rotura, max_fuerza,
    prob_enlace_base, click_force, click_radius
)


# ===================================================================
# KERNELS DEL ORQUESTADOR
# ===================================================================

@ti.kernel
def update_grid():
    """Actualiza grid espacial GLOBAL Y filtra visibles para render."""
    grid_count.fill(0)
    n_visible[None] = 0
    
    min_x, min_y = sim_bounds[0], sim_bounds[1]
    max_x, max_y = sim_bounds[2], sim_bounds[3]
    
    for i in range(n_particles[None]):
        if is_active[i]:
            p = pos[i]
            
            # 1. Agregar al grid espacial GLOBAL
            gx = int(p.x / GRID_CELL_SIZE)
            gy = int(p.y / GRID_CELL_SIZE)
            if 0 <= gx < GRID_RES and 0 <= gy < GRID_RES:
                idx = ti.atomic_add(grid_count[gx, gy], 1)
                if idx < 32:
                    grid_pids[gx, gy, idx] = i
            
            # 2. CULLING: Agregar a lista de visibles solo si está en pantalla
            if (min_x < p.x < max_x and min_y < p.y < max_y):
                vis_idx = ti.atomic_add(n_visible[None], 1)
                if vis_idx < MAX_PARTICLES:
                    visible_indices[vis_idx] = i


@ti.kernel
def count_active_particles_gpu():
    """Cuenta partículas activas (One-off per frame)."""
    active_particles_count[None] = 0
    min_x, min_y = sim_bounds[0], sim_bounds[1]
    max_x, max_y = sim_bounds[2], sim_bounds[3]
    
    for i in range(n_particles[None]):
        if is_active[i]:
            p = pos[i]
            if min_x < p.x < max_x and min_y < p.y < max_y:
                ti.atomic_add(active_particles_count[None], 1)


def simulation_step_gpu():
    """Ejecuta un único paso de simulación completo en GPU."""
    # 1. Pre-step: Aplicar fuerzas y predecir posición
    physics_pre_step()
    
    # 2. PBD Solver: Iterar restricciones
    for _ in range(SOLVER_ITERATIONS):
        update_grid()
        resolve_constraints_grid()
        apply_bond_forces_gpu()
    
    # 3. Post-step: Derivar velocidad final
    physics_post_step()
    
    # 4. Química: Formar/romper enlaces
    check_bonding_gpu()
    
    # 5. Física Avanzada (cada N frames para performance)
    apply_brownian_motion_gpu()
    apply_coulomb_repulsion_gpu()
    
    # 6. Efectos Evolutivos
    apply_evolutionary_effects_gpu()


@ti.kernel
def apply_force_pulse(center_x: ti.f32, center_y: ti.f32, power_mult: ti.f32):
    """Aplica una onda de choque expansiva en una coordenada (O(N))."""
    strength = click_force[None] * power_mult
    radius = click_radius[None]
    
    for i in range(n_particles[None]):
        if is_active[i]:
            diff = pos[i] - ti.Vector([center_x, center_y])
            dist = diff.norm()
            if dist < radius and dist > 0.01:
                vel[i] += diff.normalized() * strength


def run_simulation_fast(n_steps: int):
    """
    Ejecuta N pasos de simulación con un solo update de Grid por paso (Alta Velocidad).
    """
    for _ in range(n_steps):
        simulation_step_gpu()


# ===================================================================
# SINCRONIZACIÓN CPU <-> GPU
# ===================================================================

def sync_to_gpu(universe):
    """Sincroniza datos de CPU a GPU."""
    if universe is None:
        return
    
    # Obtener datos del universo
    positions = getattr(universe, 'positions', None)
    velocities = getattr(universe, 'velocities', None)
    radii_data = getattr(universe, 'radii', None)
    active_data = getattr(universe, 'is_active', None)
    atoms_data = getattr(universe, 'atom_types', None)
    
    n = len(positions) if positions is not None else 0
    n_particles[None] = n
    
    if n == 0:
        return
    
    # Posiciones
    if positions is not None:
        pos_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
        pos_np[:n] = positions[:n]
        pos.from_numpy(pos_np)
    
    # Velocidades
    if velocities is not None:
        vel_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
        vel_np[:n] = velocities[:n]
        vel.from_numpy(vel_np)
    
    # Radios
    if radii_data is not None:
        radii_np = np.zeros(MAX_PARTICLES, dtype=np.float32)
        radii_np[:n] = radii_data[:n]
        radii.from_numpy(radii_np)
    
    # Activos
    if active_data is not None:
        active_np = np.zeros(MAX_PARTICLES, dtype=np.int32)
        active_np[:n] = active_data[:n].astype(np.int32)
        is_active.from_numpy(active_np)
    
    # Tipos de átomo
    if atoms_data is not None:
        atoms_np = np.zeros(MAX_PARTICLES, dtype=np.int32)
        atoms_np[:n] = atoms_data[:n].astype(np.int32)
        atom_types.from_numpy(atoms_np)
        
        # Colores basados en tipo
        colors_table = (cfg.COLORES / 255.0).astype(np.float32)
        col_np = colors_table[atoms_np]
        colors.from_numpy(col_np)


def sync_from_gpu(universe):
    """Sincroniza datos de GPU a CPU."""
    if universe is None:
        return
    
    n = n_particles[None]
    
    # Solo los datos necesarios
    pos_np = pos.to_numpy()[:n]
    vel_np = vel.to_numpy()[:n]
    
    if hasattr(universe, 'positions'):
        universe.positions[:n] = pos_np
    if hasattr(universe, 'velocities'):
        universe.velocities[:n] = vel_np


def sync_positions_only(universe):
    """Solo sincroniza posiciones para renderizado (rápido)."""
    if universe is not None and hasattr(universe, 'positions'):
        universe.positions[:n_particles[None]] = pos.to_numpy()[:n_particles[None]]


def run_simulation_gpu(universe, time_scale=1, sync_full=False):
    """
    Ejecuta múltiples pasos de simulación en GPU.
    
    Args:
        universe: Universo de simulación
        time_scale: Número de pasos a ejecutar
        sync_full: Si True, sincroniza todo (lento). Si False, solo posiciones (rápido).
    """
    sync_to_gpu(universe)
    
    for _ in range(time_scale):
        simulation_step_gpu()
    
    if sync_full:
        sync_from_gpu(universe)
    else:
        sync_positions_only(universe)
