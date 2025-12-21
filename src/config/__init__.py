"""
Módulo de Configuración - LifeSimulator
========================================
Punto de entrada centralizado para toda la configuración.

Uso:
    from src.config import sim_config, ATOMS, UIConfig
    
    # O importar todo:
    import src.config as cfg
    cfg.sim_config.GRAVITY = 0.1
"""

# Re-exportar desde módulos específicos
from src.config.simulation import SimulationConfig, sim_config
from src.config.atoms import (
    ATOMS, 
    TIPOS_NOMBRES, 
    COLORES, 
    RADIOS, 
    MASAS, 
    VALENCIAS, 
    ELECTRONEG_DATA,
    load_atoms_from_json
)
from src.config.ui import UIConfig, UIWidgets
from src.config.system_constants import (
    # Escala
    WORLD_SIZE, VISUAL_SCALE, INITIAL_ZOOM,
    # Límites
    MAX_PARTICLES, DEFAULT_PARTICLES, MAX_VALENCE, MAX_BONDS,
    # Grid
    GRID_CELL_SIZE, GRID_RES, MAX_PER_CELL,
    # Velocidad
    MAX_SPEED, MAX_FORCE,
    # Visuales
    ATOM_SIZE_GL, BOND_WIDTH, DIST_EQUILIBRIO,
    # Enlaces
    RANGO_ENLACE_MIN, RANGO_ENLACE_MAX, DIST_ROTURA,
    # Interacción
    CLICK_FORCE, CLICK_RADIUS,
    # Spawn
    ATOM_SPAWN_PROBS
)

# Para compatibilidad hacia atrás
__all__ = [
    # Simulation
    'SimulationConfig',
    'sim_config',
    
    # Atoms
    'ATOMS',
    'TIPOS_NOMBRES',
    'COLORES',
    'RADIOS',
    'MASAS',
    'VALENCIAS',
    'ELECTRONEG_DATA',
    'load_atoms_from_json',
    
    # UI
    'UIConfig',
    'UIWidgets',
]
