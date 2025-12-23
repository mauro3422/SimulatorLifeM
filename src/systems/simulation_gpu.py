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
from src.core.perf_logger import get_perf_logger
from src.systems.physics_constants import SOLVER_ITERATIONS
from src.core.context import get_context

state = get_context()

# ===================================================================
# IMPORTS DE KERNELS
# ===================================================================
from src.systems.physics_kernels import (
    physics_pre_step_i,
    physics_post_step_i,
    resolve_constraints_grid_i
)

# Kernels de química
from src.systems.chemistry_kernels import (
    apply_bond_forces_i,
    apply_vsepr_geometry_i,
    check_bonding_func_single,
    compute_depth_z_i,
    update_partial_charges,
    reset_molecule_ids, propagate_molecule_ids_step,
    apply_dihedral_forces_gpu
)

# Campos Taichi
from src.systems.taichi_fields import (
    # Constantes
    MAX_PARTICLES, SOLVER_ITERATIONS, GRID_CELL_SIZE, GRID_RES, MAX_PER_CELL,
    
    # Campos de partículas
    pos, vel, radii, is_active, atom_types, n_particles,
    pos_normalized, colors,
    pos_z,  # 2.5D depth field
    
    # Campos de química
    # Campos de química
    manos_libres, enlaces_idx, num_enlaces,
    molecule_id, next_molecule_id, needs_propagate,
    
    # Grid espacial
    grid_count, grid_pids, sim_bounds,
    visible_indices, n_visible,
    
    # Contadores
    active_particles_count, total_bonds_count,
    total_mutations, total_tunnels, n_simulated_physics,
    
    # Parámetros
    gravity, friction, temperature, max_speed,
    world_width, world_height,
    dist_equilibrio, spring_k, damping,
    rango_enlace_min, rango_enlace_max, dist_rotura, max_fuerza,
    prob_enlace_base, click_force, click_radius,
    charge_factor,
    medium_type, medium_viscosity, medium_polarity
)

from src.config.system_constants import MAX_BONDS, MAX_PARTICLES

# Kernels y Campos de renderizado (para compactar datos)
from src.renderer.opengl_kernels import (
    universal_gpu_buffer,
    compact_render_data,
    prepare_bond_lines_gl,
    prepare_highlights,
    highlight_pos,
    highlight_col,
    border_vertices,
    screen_box_vertices,
    bond_vertices,
    update_borders_gl
)


# ===================================================================
# KERNELS DEL ORQUESTADOR
# ===================================================================

@ti.func
def update_grid_i(i: ti.i32):
    """Lógica de grid y visibilidad para una partícula."""
    if is_active[i]:
        p = pos[i]
        
        # 1. Agregar al grid espacial GLOBAL (para colisiones)
        gx = int(p.x / GRID_CELL_SIZE)
        gy = int(p.y / GRID_CELL_SIZE)
        if 0 <= gx < GRID_RES and 0 <= gy < GRID_RES:
            idx = ti.atomic_add(grid_count[gx, gy], 1)
            if idx < MAX_PER_CELL:
                grid_pids[gx, gy, idx] = i
        
        # 2. CULLING: Para render
        if (sim_bounds[0] < p.x < sim_bounds[2] and sim_bounds[1] < p.y < sim_bounds[3]):
            vis_idx = ti.atomic_add(n_visible[None], 1)
            if vis_idx < MAX_PARTICLES:
                visible_indices[vis_idx] = i

@ti.kernel
def update_grid():
    grid_count.fill(0)
    n_visible[None] = 0
    for i in range(n_particles[None]):
        update_grid_i(i)


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


def update_grid_orchestrator():
    """Actualiza la grilla espacial (O(N))."""
    update_grid()


# Global Frame Counter for Interleaving
sim_frame_counter = 0

@ti.kernel
def kernel_pre_step_fused():
    """Fusión O(N): Pre-paso + Actualización de Grid."""
    grid_count.fill(0)
    n_visible[None] = 0
    n_simulated_physics[None] = 0
    for i in range(n_particles[None]):
        physics_pre_step_i(i)
        update_grid_i(i)

@ti.kernel
def kernel_resolve_constraints():
    """Fusión O(N): Colisiones + Fuerzas de Enlace + Geometría VSEPR + Profundidad 2.5D."""
    for i in range(n_particles[None]):
        resolve_constraints_grid_i(i)
        apply_bond_forces_i(i)
        apply_vsepr_geometry_i(i)  # VSEPR: Mantener ángulos de enlace
        compute_depth_z_i(i)       # 2.5D: Calcular profundidad visual

@ti.kernel
def kernel_post_step_fused(t_total: ti.f32, run_advanced: ti.i32):
    """Fusión O(N): Post-paso (velocidad) + Efectos Especiales."""
    for i in range(n_particles[None]):
        physics_post_step_i(i, t_total, run_advanced)

@ti.kernel
def kernel_bonding():
    """Química Paso 2: Formación de enlaces (O(N) Paralelo)."""
    for i in range(n_particles[None]):
        check_bonding_func_single(i)
    
    # DEBUG: Print bonding params every 100 frames (approximate via total_bonds)
    # Note: This print happens in parallel, may cause issues - use atomic counter instead


@ti.kernel
def init_molecule_ids():
    """Initialize molecule IDs for all particles."""
    # Start next ID counter safely above max particle index
    next_molecule_id[None] = MAX_PARTICLES + 1
    
    for i in range(n_particles[None]):
        if is_active[i] != 0:
            molecule_id[i] = i
            needs_propagate[i] = 0


def simulation_step_gpu(steps: int = 1):
    """
    Orquestador estable y optimizado.
    """
    global sim_frame_counter
    sim_frame_counter += 1
    
    perf = get_perf_logger()
    
    if n_particles[None] == 0:
        # Nuclear fallback for stress test sterility
        n_particles[None] = 5000 
        for i in range(5000): is_active[i] = 1
        print(f"☢️ NUCLEAR: Forced n_particles=5000 at frame {sim_frame_counter}!")

    # DEBUG: Print every 1000 frames (reduced from 100)
    if sim_frame_counter % 1000 == 0:
        print(f"[SIM DEBUG] Frame {sim_frame_counter} | n_particles={n_particles[None]} | steps={steps}")
        print(f"[SIM DEBUG] sim_bounds={sim_bounds[0]}, {sim_bounds[1]}, {sim_bounds[2]}, {sim_bounds[3]}")
        print(f"[SIM DEBUG] grid_count sum={grid_count.to_numpy().sum()} | n_simulated={n_simulated_physics[None]}")

    run_bonding = True # Force bonding every call for debug
    run_advanced = (sim_frame_counter % 2 == 0)

    perf.start("physics")
    
    # Initialize Medium if first frame
    if sim_frame_counter == 1:
        from src.systems.physics_constants import (
            MEDIUM_TYPE_WATER, MEDIUM_VISCOSITY_DEFAULT, MEDIUM_POLARITY_DEFAULT
        )
        medium_type[None] = MEDIUM_TYPE_WATER
        medium_viscosity[None] = MEDIUM_VISCOSITY_DEFAULT
        medium_polarity[None] = MEDIUM_POLARITY_DEFAULT
        print(f"[INIT] Medium set to WATER (V={medium_viscosity[None]}, P={medium_polarity[None]})")

    for _ in range(steps):
        # 1. Pre + Grid (1 Dispatch)
        kernel_pre_step_fused()
        
        # 1b. Torsiones (Diedros) - Antes del solver para que afecten velocidades
        apply_dihedral_forces_gpu()
        
        # 1c. Cargas Dinámicas (UFF) - Para electrostática y Puentes de Hidrógeno
        update_partial_charges()
        
        # DEBUG: Test bonding immediately after grid population
        if sim_frame_counter == 1:
            print(f"[DEBUG] Testing bonding IMMEDIATELY after grid pop...")
            from src.systems.taichi_fields import debug_particles_checked, debug_neighbors_found, debug_distance_passed, debug_prob_passed
            debug_particles_checked[None] = 0
            debug_neighbors_found[None] = 0
            debug_distance_passed[None] = 0
            debug_prob_passed[None] = 0
            kernel_bonding()
            ti.sync()
            print(f"[EARLY BONDING] particles_checked={debug_particles_checked[None]}, prob_passed={debug_prob_passed[None]}")
            print(f"[EARLY BONDING] neighbors_found={debug_neighbors_found[None]}, distance_passed={debug_distance_passed[None]}")
            print(f"[EARLY BONDING] total_bonds={total_bonds_count[None]}")
        
        # 2. Solver (M Dispatches - Necesarios para sincronización global)
        # Nota: Aquí sí lanzamos M veces para que los partículas vean posiciones actualizadas
        for _ in range(SOLVER_ITERATIONS):
            kernel_resolve_constraints()
            
        # 3. Post (1 Dispatch - Fusión Total: Física + Reglas Avanzadas)
        from src.systems.physics_constants import BROWNIAN_BASE_TEMP
        t_total = BROWNIAN_BASE_TEMP + temperature[None]
        kernel_post_step_fused(t_total, 1 if run_advanced else 0)
        
        # 4. Química (1 Dispatch ocasional)
        
        # DEBUG: Verify grid just before bonding (frame 1 only)
        if sim_frame_counter == 1:
            grid_sum = grid_count.to_numpy().sum()
            print(f"[PRE-BONDING] grid_count sum = {grid_sum}")
            print(f"[PRE-BONDING] manos_libres sum = {manos_libres.to_numpy().sum()}")
            
            # Check where particles are in the grid
            gc_np = grid_count.to_numpy()
            max_cell = np.unravel_index(np.argmax(gc_np), gc_np.shape)
            print(f"[PRE-BONDING] Max cell: {max_cell} with {gc_np[max_cell]} particles")
            
            # Check first few PIDs in that cell
            gp_np = grid_pids.to_numpy()
            pids_sample = gp_np[max_cell[0], max_cell[1], :5]
            print(f"[PRE-BONDING] First 5 PIDs in max cell: {pids_sample}")
            
            # Check manos_libres for those specific particles
            manos_np = manos_libres.to_numpy()
            for pid in pids_sample[:5]:
                if pid >= 0:
                    print(f"[PRE-BONDING] manos_libres[{pid}] = {manos_np[pid]}")
        
        # 5. Propagación de IDs de Molécula (Strategy: Reset & Resync)
        # OPTIMIZATION: Temporal Interleaving (Run every 4 frames)
        # OPTIMIZATION v2: Reduced from 16 to 8 iterations (~50% faster)
        if sim_frame_counter % 4 == 0:
            reset_molecule_ids()
            
            # 8 iterations is enough for most molecule sizes
            for _ in range(8):
                 propagate_molecule_ids_step()
        
        # DEBUG: Print bonding parameters on first step
        if sim_frame_counter == 1:
            print(f"[BONDING PARAMS] rango_enlace_max={rango_enlace_max[None]}")
            print(f"[BONDING PARAMS] prob_enlace_base={prob_enlace_base[None]}")
            print(f"[BONDING PARAMS] total_bonds={total_bonds_count[None]}")
            
            # Debug counters
            from src.systems.taichi_fields import (
                debug_particles_checked, debug_neighbors_found,
                debug_distance_passed, debug_prob_passed
            )
            print(f"[BONDING DEBUG] particles_checked={debug_particles_checked[None]}")
            print(f"[BONDING DEBUG] neighbors_found={debug_neighbors_found[None]}")
            print(f"[BONDING DEBUG] distance_passed={debug_distance_passed[None]}")
            print(f"[BONDING DEBUG] prob_passed={debug_prob_passed[None]}")
    perf.stop("physics")


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
    Ejecuta la simulación optimizada (El kernel ya maneja los pasos).
    """
    simulation_step_gpu(n_steps)


# ===================================================================
# SINCRONIZACIÓN CPU <-> GPU
# ===================================================================

def sync_to_gpu(universe):
    """Sincroniza datos de CPU a GPU."""
    if universe is None:
        return
    
    # Obtener datos del universo
    
    # Init molecule IDs if starting
    n_existing = n_particles[None]
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
        
        # Initialize molecule IDs if this is a fresh start/load
        if n_existing == 0:
            init_molecule_ids()
            print("[GPU] Initialized molecule IDs")
        
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
