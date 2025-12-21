"""
Constantes Físicas Centralizadas - LifeSimulator
==================================================
Centraliza todas las constantes y fórmulas físicas para la simulación.
Escaladas para funcionar a escala de simulación (no escala real atómica).

FÍSICA IMPLEMENTADA:
1. PBD (Position Based Dynamics) - Müller et al. 2007
2. Ley de Hooke (enlaces) - F = -k * (x - x₀)
3. Ley de Coulomb (repulsión) - F = k * q₁q₂ / r²
4. Movimiento Browniano - v_rms = √(k_B * T / m)
"""

import numpy as np

# ==============================================================================
# ESCALA DE SIMULACIÓN
# ==============================================================================
# Factor de escala maestro: 1.0 = escala base, >1 = mundo más grande
SIMULATION_SCALE = 3.0

# Mundo en unidades de simulación (no metros)
WORLD_SIZE = 15000  # Unidades de simulación


# ==============================================================================
# FÍSICA: MOVIMIENTO BROWNIANO (Agitación Térmica)
# ==============================================================================
# Fórmula: v_rms = √(k_B * T / m)
# - k_B: Constante de Boltzmann simulada
# - T: Temperatura (0.0 = congelado, 1.0 = muy caliente)
# - m: Masa atómica relativa

BROWNIAN_K = 0.1            # Constante de Boltzmann simulada
BROWNIAN_BASE_TEMP = 0.05   # Temperatura ambiente mínima (siempre hay algo de agitación)


# ==============================================================================
# FÍSICA: LEY DE COULOMB (Repulsión Electrostática)
# ==============================================================================
# Fórmula: F = k * |q₁ * q₂| / r²
# - k: Constante de Coulomb simulada
# - q: Carga parcial basada en electronegatividad
# - r: Distancia entre partículas

COULOMB_K = 50.0            # Intensidad de repulsión
REPULSION_MIN_DIST = 5.0    # Distancia mínima (evita singularidades)
REPULSION_MAX_DIST = 50.0   # Distancia máxima de efecto
CHARGE_FACTOR = 0.2         # Factor de conversión electroneg -> carga
ELECTRONEG_AVERAGE = 2.82   # Electronegatividad media (referencia)


# ==============================================================================
# FÍSICA: LEY DE HOOKE (Enlaces Químicos)
# ==============================================================================
# Fórmula: F = -k * (x - x₀) - c * v_rel
# - k: Constante del resorte (spring_k)
# - x₀: Distancia de equilibrio
# - c: Constante de amortiguamiento (damping)
# - v_rel: Velocidad relativa (proyectada)

SPRING_K_DEFAULT = 1.5          # Rigidez del enlace
DAMPING_DEFAULT = 2.0           # Amortiguamiento (reduce oscilaciones)
DIST_EQUILIBRIO_BASE = 35.0     # Distancia de equilibrio base (escala 1.0)
DIST_ROTURA_FACTOR = 1.5        # Factor de rotura (dist_rotura = rango_max * factor)


# ==============================================================================
# FÍSICA: PBD (Position Based Dynamics)
# ==============================================================================
# Referencia: Müller et al. 2007 - "Position Based Dynamics"
# Pasos: predecir -> resolver restricciones -> derivar velocidad

SOLVER_ITERATIONS = 3       # Iteraciones de Gauss-Seidel
VELOCITY_DERIVATION = 0.9   # Factor de derivación (pos - pos_old) * factor
COLLISION_CORRECTION = 0.7  # Factor de corrección de colisión


# ==============================================================================
# LÍMITES DE SEGURIDAD (Evitan inestabilidades numéricas)
# ==============================================================================
MAX_VELOCITY_BASE = 8.0     # Velocidad máxima base (escala 1.0)
MAX_FORCE_BASE = 20.0       # Fuerza máxima base (escala 1.0)
FRICTION_DEFAULT = 0.95     # Coeficiente de fricción del medio


# ==============================================================================
# QUÍMICA: PARÁMETROS DE ENLACE
# ==============================================================================
RANGO_ENLACE_MIN_BASE = 2.0     # Distancia mínima para formar enlace
RANGO_ENLACE_MAX_BASE = 70.0    # Distancia máxima para formar enlace
PROB_ENLACE_REALISTA = 0.3      # Probabilidad base (modo realista)
PROB_ENLACE_ARCADE = 0.8        # Probabilidad base (modo arcade)
MAX_VALENCE = 8                 # Máximo número de enlaces por átomo


# ==============================================================================
# EFECTOS ESPECIALES (Evolutivos)
# ==============================================================================
MUTATION_PROBABILITY = 0.00005  # Probabilidad de mutación por frame
TUNNEL_VELOCITY_THRESHOLD = 0.95  # % de max_speed para activar túnel
TUNNEL_PROBABILITY = 0.01       # Probabilidad de efecto túnel
TUNNEL_JUMP_DISTANCE = 60.0     # Distancia del salto cuántico


# ==============================================================================
# FUNCIONES DE UTILIDAD
# ==============================================================================

def scale_parameter(base_value: float, scale: float = SIMULATION_SCALE) -> float:
    """Escala un parámetro base según el factor de escala de simulación."""
    return base_value * scale


def get_scaled_physics():
    """Retorna todos los parámetros físicos escalados."""
    return {
        'dist_equilibrio': scale_parameter(DIST_EQUILIBRIO_BASE),
        'spring_k': SPRING_K_DEFAULT,
        'damping': scale_parameter(DAMPING_DEFAULT),
        'max_speed': scale_parameter(MAX_VELOCITY_BASE),
        'max_fuerza': scale_parameter(MAX_FORCE_BASE),
        'rango_enlace_min': scale_parameter(RANGO_ENLACE_MIN_BASE),
        'rango_enlace_max': scale_parameter(RANGO_ENLACE_MAX_BASE),
    }


def calculate_brownian_velocity(temperature: float, mass: float) -> float:
    """
    Calcula la velocidad RMS para movimiento Browniano.
    
    Args:
        temperature: Temperatura de simulación (0.0 - 1.0)
        mass: Masa atómica relativa
        
    Returns:
        Velocidad RMS
    """
    T_total = BROWNIAN_BASE_TEMP + temperature
    return np.sqrt(BROWNIAN_K * T_total / mass)


def calculate_coulomb_force(q1: float, q2: float, distance: float) -> float:
    """
    Calcula la magnitud de la fuerza de Coulomb.
    
    Args:
        q1, q2: Cargas parciales
        distance: Distancia entre partículas
        
    Returns:
        Magnitud de la fuerza (positivo = repulsión)
    """
    if distance < REPULSION_MIN_DIST:
        distance = REPULSION_MIN_DIST
    return COULOMB_K * abs(q1 * q2) / (distance * distance)


def electroneg_to_charge(electroneg: float) -> float:
    """Convierte electronegatividad a carga parcial."""
    return (electroneg - ELECTRONEG_AVERAGE) * CHARGE_FACTOR
