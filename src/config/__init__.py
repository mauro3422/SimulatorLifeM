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
