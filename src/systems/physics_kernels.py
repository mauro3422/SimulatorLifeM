"""
Physics Kernels - Taichi GPU Kernels para Física
=================================================
Kernels de física básica: gravedad, fricción, colisiones,
movimiento Browniano y repulsión de Coulomb.
"""
import taichi as ti

from src.systems.taichi_fields import (
    # Constantes
    GRID_CELL_SIZE, GRID_RES,
    BROWNIAN_K, BROWNIAN_BASE_TEMP,
    COULOMB_K, REPULSION_MIN_DIST, REPULSION_MAX_DIST,
    ELECTRONEG_AVG,
    
    # Campos de partículas
    pos, vel, pos_old, radii, is_active, atom_types,
    
    # Campos de física
    n_particles, gravity, friction, temperature, max_speed,
    world_width, world_height,
    
    # Grid espacial
    grid_count, grid_pids,
    
    # Datos atómicos
    ELECTRONEG, MASAS_ATOMICAS
)


# ===================================================================
# FÍSICA BÁSICA
# ===================================================================

@ti.kernel
def physics_pre_step():
    """Fuerzas iniciales y predicción de posición - GLOBAL."""
    for i in range(n_particles[None]):
        if is_active[i]:
            vel[i].y += gravity[None] * 5.0
            vel[i] *= friction[None]
            
            if temperature[None] > 0:
                vel[i] += ti.Vector([ti.random()-0.5, ti.random()-0.5]) * temperature[None] * 20.0

            speed = vel[i].norm()
            if speed > max_speed[None]:
                vel[i] = vel[i] / speed * max_speed[None]
            
            pos_old[i] = pos[i]
            pos[i] += vel[i]


@ti.kernel
def physics_post_step():
    """Derivar velocidad final - GLOBAL."""
    for i in range(n_particles[None]):
        if is_active[i]:
            vel[i] = (pos[i] - pos_old[i]) * 0.9


@ti.kernel
def resolve_constraints_grid():
    """Resolver colisiones y paredes - GLOBAL (via grid)."""
    for i in range(n_particles[None]):
        if is_active[i]:
            # Paredes
            r = radii[i]
            if pos[i][0] < r: pos[i][0] = r
            if pos[i][0] > world_width[None] - r: pos[i][0] = world_width[None] - r
            if pos[i][1] < r: pos[i][1] = r
            if pos[i][1] > world_height[None] - r: pos[i][1] = world_height[None] - r
            
            # Colisiones via grid
            gx = int(pos[i][0] / GRID_CELL_SIZE)
            gy = int(pos[i][1] / GRID_CELL_SIZE)
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neighbors = ti.min(32, grid_count[nx, ny])
                    for k in range(num_neighbors):
                        j = grid_pids[nx, ny, k]
                        if i < j:
                            diff = pos[i] - pos[j]
                            dist = diff.norm()
                            sum_radii = radii[i] + radii[j]
                            if 0.001 < dist < sum_radii:
                                overlap = sum_radii - dist
                                correction = (diff / dist) * overlap * 0.7
                                pos[i] += correction * 0.5
                                pos[j] -= correction * 0.5


# ===================================================================
# MOVIMIENTO BROWNIANO
# ===================================================================

@ti.kernel
def apply_brownian_motion_gpu():
    """Aplica movimiento Browniano (agitación térmica) GLOBAL."""
    T_total = BROWNIAN_BASE_TEMP + temperature[None]
    for i in range(n_particles[None]):
        if is_active[i]:
            atom_type = atom_types[i]
            mass = MASAS_ATOMICAS[atom_type]
            
            # Velocidad RMS = sqrt(k * T / m)
            v_rms = ti.sqrt(BROWNIAN_K * T_total / mass)
            
            # Dirección aleatoria
            dx = ti.random() - 0.5
            dy = ti.random() - 0.5
            length = ti.sqrt(dx*dx + dy*dy) + 1e-8
            dx /= length
            dy /= length
            
            # Magnitud aleatoria
            magnitude = v_rms * ti.random()
            
            vel[i] += ti.Vector([dx * magnitude, dy * magnitude])


# ===================================================================
# REPULSIÓN DE COULOMB
# ===================================================================

@ti.kernel
def apply_coulomb_repulsion_gpu():
    """Repulsión de Coulomb GLOBAL."""
    charge_factor = 0.2
    for i in range(n_particles[None]):
        if is_active[i]:
            # Carga parcial basada en electronegatividad
            type_i = atom_types[i]
            q_i = (ELECTRONEG[type_i] - ELECTRONEG_AVG) * charge_factor
            mass_i = MASAS_ATOMICAS[type_i]
            
            # Buscar vecinos cercanos en el grid
            gx = int(pos[i][0] / GRID_CELL_SIZE)
            gy = int(pos[i][1] / GRID_CELL_SIZE)
            
            total_force = ti.Vector([0.0, 0.0])
            
            for ox, oy in ti.static(ti.ndrange((-1, 2), (-1, 2))):
                nx, ny = gx + ox, gy + oy
                if 0 <= nx < GRID_RES and 0 <= ny < GRID_RES:
                    num_neighbors = ti.min(32, grid_count[nx, ny])
                    for k in range(num_neighbors):
                        j = grid_pids[nx, ny, k]
                        if i != j:
                            diff = pos[i] - pos[j]
                            dist = diff.norm()
                            
                            if REPULSION_MIN_DIST < dist < REPULSION_MAX_DIST:
                                type_j = atom_types[j]
                                q_j = (ELECTRONEG[type_j] - ELECTRONEG_AVG) * charge_factor
                                
                                # Solo repeler si ambos tienen misma carga (mismo signo)
                                if q_i * q_j > 0:
                                    # Ley de Coulomb: F = k * |q1 * q2| / r²
                                    dist_sq = ti.max(dist * dist, REPULSION_MIN_DIST * REPULSION_MIN_DIST)
                                    force_mag = COULOMB_K * ti.abs(q_i * q_j) / dist_sq
                                    
                                    direction = diff / dist
                                    total_force += direction * force_mag
            
            # Aplicar fuerza dividida por masa (F = ma → a = F/m)
            vel[i] += total_force / mass_i * 0.1


# ===================================================================
# UTILIDADES
# ===================================================================

@ti.kernel
def shake_simulation():
    """Añade caos masivo para desatascar partículas."""
    for i in range(n_particles[None]):
        vel[i] += ti.Vector([ti.random()-0.5, ti.random()-0.5]) * 20.0
