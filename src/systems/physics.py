"""
Position Based Dynamics (PBD) Physics Engine
Based on: Müller et al. 2007 - "Position Based Dynamics"

Este motor reemplaza la integración Euler por un sistema basado en restricciones.
"""
import numpy as np
import src.config as cfg
from src.core.logger import log_stability

# Configuración del Solver
SOLVER_ITERATIONS = 4  # Número de iteraciones Gauss-Seidel

def pbd_step(universe, spatial_grid=None):
    """
    Un paso completo de Position Based Dynamics.
    
    Args:
        universe: El universo de simulación
        spatial_grid: SpatialGrid opcional para optimización O(N)
    """
    # Máscara de partículas activas (no durmiendo)
    active = ~universe.is_sleeping
    
    # 0. Guardar posición anterior (para derivar velocidad)
    universe.pos_old = universe.pos.copy()
    
    # 1. Aplicar fuerzas externas a la velocidad (SOLO ACTIVAS)
    # Gravedad
    universe.vel[active, 1] += universe.config.GRAVITY * 10.0
    
    # Temperatura (agitación térmica)
    if universe.config.TEMPERATURE > 0:
        universe.vel[active] += np.random.randn(np.sum(active), 2) * universe.config.TEMPERATURE * 0.5
    
    # 2. Amortiguar velocidad (fricción del medio)
    universe.vel[active] *= universe.config.FRICTION
    
    # Limitar velocidad máxima para estabilidad
    max_speed = universe.config.MAX_VELOCIDAD
    speed = np.linalg.norm(universe.vel, axis=1, keepdims=True)
    mask = speed > max_speed
    universe.vel = np.where(mask, universe.vel / speed * max_speed, universe.vel)
    
    # 3. Predecir nuevas posiciones
    universe.pos[active] = universe.pos[active] + universe.vel[active]
    
    # 4. Resolver restricciones iterativamente (Gauss-Seidel)
    for _ in range(SOLVER_ITERATIONS):
        _solve_wall_constraints(universe)
        _solve_particle_constraints(universe, spatial_grid)
    
    # 5. Derivar velocidad del cambio de posición (Verlet implícito)
    universe.vel = (universe.pos - universe.pos_old) * 0.9
    
    # 6. SLEEPING SYSTEM: Actualizar estado de dormido
    speeds = np.linalg.norm(universe.vel, axis=1)
    
    # Partículas muy lentas incrementan contador de sueño
    slow_mask = speeds < universe.SLEEP_THRESHOLD
    universe.sleep_counter[slow_mask] += 1
    universe.sleep_counter[~slow_mask] = 0  # Reset si se mueve
    
    # Dormir si ha estado quieto suficiente tiempo
    universe.is_sleeping = universe.sleep_counter >= universe.SLEEP_FRAMES
    
    # Despertar si hay colisión cercana o temperatura alta
    if universe.config.TEMPERATURE > 0.05:
        universe.is_sleeping[:] = False  # Despertar todos con alta temperatura


def _solve_wall_constraints(universe):
    """Mantiene las partículas dentro de los límites."""
    limit_x = universe.config.WIDTH - 200
    limit_y = universe.config.HEIGHT
    radii = universe.radios_asignados
    
    # Límite izquierdo
    mask = universe.pos[:, 0] < radii
    universe.pos[mask, 0] = radii[mask]
    
    # Límite derecho
    mask = universe.pos[:, 0] > limit_x - radii
    universe.pos[mask, 0] = limit_x - radii[mask]
    
    # Límite superior
    mask = universe.pos[:, 1] < radii
    universe.pos[mask, 1] = radii[mask]
    
    # Límite inferior
    mask = universe.pos[:, 1] > limit_y - radii
    universe.pos[mask, 1] = limit_y - radii[mask]


def _solve_particle_constraints(universe, spatial_grid=None):
    """
    Resuelve solapamientos entre partículas empujándolas simétricamente.
    Usa Spatial Hashing si está disponible para O(N) en vez de O(N²).
    """
    pos = universe.pos
    radii = universe.radios_asignados
    n = len(pos)
    
    if spatial_grid is not None:
        # MODO OPTIMIZADO: Solo revisar pares potenciales
        spatial_grid.insert_all(pos)
        pairs = spatial_grid.get_potential_pairs(pos)
        
        # Acumular correcciones
        total_correction = np.zeros_like(pos)
        
        for i, j in pairs:
            diff = pos[i] - pos[j]
            dist = np.linalg.norm(diff)
            sum_r = radii[i] + radii[j]
            
            if dist < sum_r and dist > 0:
                overlap = sum_r - dist
                direction = diff / dist
                correction = direction * overlap * 0.5
                total_correction[i] += correction
                total_correction[j] -= correction
        
        universe.pos -= total_correction
    else:
        # MODO FALLBACK: O(N²) completo
        diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
        dist_sq = np.sum(diff**2, axis=2)
        dist = np.sqrt(dist_sq)
        
        sum_radii = radii[:, np.newaxis] + radii[np.newaxis, :]
        overlap = sum_radii - dist
        overlap_mask = overlap > 0
        np.fill_diagonal(overlap_mask, False)
        
        if not np.any(overlap_mask):
            return
        
        with np.errstate(divide='ignore', invalid='ignore'):
            direction = diff / (dist[:, :, np.newaxis] + 1e-9)
        direction = np.nan_to_num(direction)
        
        correction = direction * (overlap[:, :, np.newaxis] * 0.5)
        correction[~overlap_mask] = 0
        
        total_correction = np.sum(correction, axis=1)
        universe.pos -= total_correction


def get_collision_mask(universe):
    """
    Devuelve la máscara de colisiones actual (para debug y química).
    """
    pos = universe.pos
    radii = universe.radios_asignados
    
    diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
    dist = np.linalg.norm(diff, axis=2)
    sum_radii = radii[:, np.newaxis] + radii[np.newaxis, :]
    
    collision_mask = dist < sum_radii
    np.fill_diagonal(collision_mask, False)
    
    return collision_mask
