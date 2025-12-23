"""
Chemistry Constants - Constantes Químicas y VSEPR
===================================================
Contiene constantes para geometría molecular VSEPR,
hibridación y ángulos de enlace ideales.

VSEPR = Valence Shell Electron Pair Repulsion
Teoría que predice la geometría molecular basada en
la repulsión de pares de electrones.
"""

import math

# ==============================================================================
# ÁNGULOS DE ENLACE VSEPR (Grados)
# ==============================================================================
# Basado en geometría VSEPR para diferentes números de coordinación
# Valencia = número de átomos enlazados + pares solitarios

# Geometrías ideales por número de regiones de electrones
VSEPR_ANGLES = {
    2: 180.0,    # Linear (CO2, BeCl2)
    3: 120.0,    # Trigonal plana (BF3)
    4: 109.5,    # Tetraédrica (CH4) - ángulo ideal
    5: 90.0,     # Bipiramidal trigonal (PCl5) - ecuatorial
    6: 90.0,     # Octaédrica (SF6)
}

# Ángulos específicos por tipo de molécula
MOLECULAR_ANGLES = {
    # Agua H2O: 2 enlaces + 2 pares solitarios = 4 regiones, pero ángulo menor
    'H2O': 104.5,
    # Amoníaco NH3: 3 enlaces + 1 par solitario
    'NH3': 107.0,
    # Metano CH4: 4 enlaces, tetraédrico perfecto
    'CH4': 109.5,
    # Eteno C2H4: Doble enlace, trigonal plana
    'C2H4': 120.0,
    # Dióxido de carbono CO2: Lineal
    'CO2': 180.0,
}


# ==============================================================================
# HIBRIDACIÓN ORBITAL
# ==============================================================================
# Define el tipo de hibridación según valencia efectiva

class Hybridization:
    SP = 'sp'      # 2 orbitales, lineal, 180°
    SP2 = 'sp2'    # 3 orbitales, trigonal, 120°
    SP3 = 'sp3'    # 4 orbitales, tetraédrica, 109.5°
    SP3D = 'sp3d'  # 5 orbitales, bipiramidal
    SP3D2 = 'sp3d2'  # 6 orbitales, octaédrica


# Hibridación por tipo de átomo y número de enlaces
# Format: ATOM_TYPE_INDEX: {num_bonds: (hybridization, ideal_angle)}
ATOM_HYBRIDIZATION = {
    # C (índice 0) - Variable según enlaces
    0: {
        2: (Hybridization.SP, 180.0),     # Triple enlace (acetileno)
        3: (Hybridization.SP2, 120.0),    # Doble enlace (eteno)
        4: (Hybridization.SP3, 109.5),    # Saturado (metano)
    },
    
    # H (índice 1) - Solo 1 enlace
    1: {1: (Hybridization.SP, 180.0)},
    
    # N (índice 2)
    2: {
        1: (Hybridization.SP, 180.0),
        2: (Hybridization.SP2, 120.0),
        3: (Hybridization.SP3, 107.0),    # NH3 con par solitario
    },
    
    # O (índice 3)
    3: {
        1: (Hybridization.SP, 180.0),
        2: (Hybridization.SP3, 104.5),    # H2O con 2 pares solitarios
    },
    
    # P (índice 4)
    4: {
        3: (Hybridization.SP3, 107.0),
        5: (Hybridization.SP3D, 90.0),
    },
    
    # S (índice 5)
    5: {
        2: (Hybridization.SP3, 104.5),
        4: (Hybridization.SP3D, 90.0),
        6: (Hybridization.SP3D2, 90.0),
    },
}


# ==============================================================================
# FUERZA DE RESTAURACIÓN ANGULAR
# ==============================================================================
# Constantes para el resorte angular que mantiene ángulos VSEPR

ANGULAR_SPRING_K = 30.0      # Higher for precision with tanh model
ANGULAR_DAMPING = 0.2        # Increased damping for the stabilized model
ANGULAR_FORCE_FACTOR = 8.0   # Higher factor for the tanh scaling

# Tolerancia de ángulo (grados) - Por debajo, no aplicar fuerza
ANGLE_TOLERANCE = 1.0  # Corrección muy temprana

# Conversión a radianes para kernels
DEG_TO_RAD = math.pi / 180.0
RAD_TO_DEG = 180.0 / math.pi


# ==============================================================================
# FUNCIONES DE UTILIDAD
# ==============================================================================

def get_ideal_angle(atom_type: int, num_bonds: int) -> float:
    """
    Retorna el ángulo ideal en grados para un átomo dado su tipo y valencia.
    
    Args:
        atom_type: Índice del tipo de átomo (0=H, 1=C, 2=N, 3=O, 4=P, 5=S)
        num_bonds: Número de enlaces del átomo
        
    Returns:
        Ángulo ideal en grados
    """
    if atom_type in ATOM_HYBRIDIZATION:
        bonds_dict = ATOM_HYBRIDIZATION[atom_type]
        if num_bonds in bonds_dict:
            _, angle = bonds_dict[num_bonds]
            return angle
    
    # Default: usar tabla VSEPR genérica
    if num_bonds in VSEPR_ANGLES:
        return VSEPR_ANGLES[num_bonds]
    
    # Fallback: 109.5° (tetraédrico)
    return 109.5


def get_ideal_angle_rad(atom_type: int, num_bonds: int) -> float:
    """Retorna el ángulo ideal en radianes."""
    return get_ideal_angle(atom_type, num_bonds) * DEG_TO_RAD
