"""
VSEPR Parameter Tuner - Búsqueda Automática de Parámetros
==========================================================
Simula matemáticamente el balance de fuerzas sin GPU para
encontrar rápidamente los valores óptimos.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
import math

# =====================================================
# SIMULADOR MATEMÁTICO (Sin GPU - Ultra Rápido)
# =====================================================

@dataclass
class Atom:
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0

@dataclass 
class WaterMolecule:
    O: Atom
    H1: Atom
    H2: Atom
    
def create_water_flat(dist: float = 105.0) -> WaterMolecule:
    """Crea una molécula de agua plana (ángulo 180°)."""
    return WaterMolecule(
        O=Atom(0, 0, 0),
        H1=Atom(-dist, 0, 0),
        H2=Atom(dist, 0, 0)
    )

def calculate_angle_3d(mol: WaterMolecule) -> float:
    """Calcula ángulo H-O-H en 3D (grados)."""
    v1 = np.array([mol.H1.x - mol.O.x, mol.H1.y - mol.O.y, mol.H1.z - mol.O.z])
    v2 = np.array([mol.H2.x - mol.O.x, mol.H2.y - mol.O.y, mol.H2.z - mol.O.z])
    
    len1, len2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if len1 < 0.001 or len2 < 0.001:
        return 0.0
    
    cos_angle = np.clip(np.dot(v1, v2) / (len1 * len2), -1, 1)
    return np.degrees(np.arccos(cos_angle))

def calculate_z_spread(mol: WaterMolecule) -> float:
    """Calcula la dispersión en Z."""
    zs = [mol.O.z, mol.H1.z, mol.H2.z]
    return max(zs) - min(zs)

# =====================================================
# FÍSICA: FUERZAS
# =====================================================

def apply_vsepr_force(mol: WaterMolecule, params: dict) -> None:
    """Aplica fuerza VSEPR angular con función suave."""
    ideal_angle = 104.5
    current_angle = calculate_angle_3d(mol)
    angle_diff_rad = np.radians(current_angle - ideal_angle)
    
    # Fuerza con función suave (tanh) para estabilidad
    K = params['angular_spring_k']
    factor = params['angular_force_factor']
    max_f = params['max_vsepr_force']
    
    # Torque suavizado
    raw_force = angle_diff_rad * K * factor
    force_mag = np.tanh(raw_force / max_f) * max_f  # Suave y acotada
    
    # Vector perpendicular en el plano XZ para empujar H fuera del plano
    # Simplificado: empujar H1 hacia +Z, H2 hacia -Z  
    if abs(angle_diff_rad) > 0.05:  # ~3 grados
        push = force_mag * 0.5
        mol.H1.vz += push if mol.H1.z < 10 else 0
        mol.H2.vz -= push if mol.H2.z > -10 else 0

def apply_bond_spring(mol: WaterMolecule, params: dict) -> None:
    """Aplica fuerzas de resorte de enlace."""
    dist_eq = params['dist_equilibrio']
    spring_k = params['spring_k']
    
    for H in [mol.H1, mol.H2]:
        dx = H.x - mol.O.x
        dy = H.y - mol.O.y
        dz = H.z - mol.O.z
        dist = np.sqrt(dx*dx + dy*dy + dz*dz)
        
        if dist > 0.001:
            # Fuerza de Hooke
            f_mag = (dist - dist_eq) * spring_k
            H.vx -= (dx/dist) * f_mag * 0.5
            H.vy -= (dy/dist) * f_mag * 0.5
            H.vz -= (dz/dist) * f_mag * 0.5

def apply_symmetry_breaking(mol: WaterMolecule, params: dict, frame: int) -> None:
    """Rompe simetría inicial."""
    strength = params['symmetry_strength']
    
    if frame < 50:  # Solo en frames iniciales
        if abs(mol.H1.z) < 5 and abs(mol.H1.vz) < 1:
            mol.H1.vz += strength
        if abs(mol.H2.z) < 5 and abs(mol.H2.vz) < 1:
            mol.H2.vz -= strength

def apply_friction(mol: WaterMolecule, params: dict) -> None:
    """Aplica fricción."""
    friction_xy = params['friction']
    friction_z = params['friction_z']
    
    for atom in [mol.O, mol.H1, mol.H2]:
        atom.vx *= friction_xy
        atom.vy *= friction_xy
        atom.vz *= friction_z

def integrate(mol: WaterMolecule, params: dict) -> None:
    """Integra posiciones."""
    max_vel = params['max_velocity']
    max_vel_z = params['max_velocity_z']
    
    for atom in [mol.O, mol.H1, mol.H2]:
        # Limitar velocidades
        speed = np.sqrt(atom.vx**2 + atom.vy**2)
        if speed > max_vel:
            atom.vx = atom.vx / speed * max_vel
            atom.vy = atom.vy / speed * max_vel
        
        atom.vz = np.clip(atom.vz, -max_vel_z, max_vel_z)
        
        # Integrar
        atom.x += atom.vx
        atom.y += atom.vy
        atom.z += atom.vz
        
        # Límites Z
        max_z = params['max_z']
        atom.z = np.clip(atom.z, -max_z, max_z)

# =====================================================
# SIMULACIÓN COMPLETA
# =====================================================

def simulate_water(params: dict, n_frames: int = 2000) -> dict:
    """Simula una molécula de agua y retorna métricas."""
    mol = create_water_flat(params['dist_equilibrio'])
    
    angle_history = []
    z_spread_history = []
    max_velocity_seen = 0
    
    for frame in range(n_frames):
        # Aplicar fuerzas
        apply_symmetry_breaking(mol, params, frame)
        apply_vsepr_force(mol, params)
        apply_bond_spring(mol, params)
        apply_friction(mol, params)
        integrate(mol, params)
        
        # Métricas
        if frame % 50 == 0:
            angle_history.append(calculate_angle_3d(mol))
            z_spread_history.append(calculate_z_spread(mol))
        
        max_v = max(abs(mol.H1.vz), abs(mol.H2.vz), abs(mol.O.vz))
        max_velocity_seen = max(max_velocity_seen, max_v)
    
    final_angle = calculate_angle_3d(mol)
    final_z_spread = calculate_z_spread(mol)
    
    return {
        'final_angle': final_angle,
        'angle_error': abs(104.5 - final_angle),
        'z_spread': final_z_spread,
        'max_velocity': max_velocity_seen,
        'converged': abs(104.5 - final_angle) < 15,
        'stable': max_velocity_seen < 100,
        'angle_history': angle_history,
    }

# =====================================================
# BÚSQUEDA DE PARÁMETROS
# =====================================================

def parameter_sweep():
    """Busca la mejor combinación de parámetros."""
    
    # Rangos de parámetros a probar (Más enfocado para velocidad)
    param_grid = {
        'angular_spring_k': [10.0, 20.0, 30.0],
        'angular_force_factor': [3.0, 5.0, 10.0],
        'max_vsepr_force': [3.0, 5.0, 10.0],
        'spring_k': [0.5, 1.0],
        'friction_z': [0.95, 0.97, 0.99],
        'symmetry_strength': [5.0, 15.0],
    }
    
    # Parámetros fijos
    fixed_params = {
        'dist_equilibrio': 105.0,
        'friction': 0.95,
        'max_velocity': 8.0,
        'max_velocity_z': 6.0,
        'max_z': 50.0,
    }
    
    best_score = float('inf')
    best_params = None
    best_result = None
    
    total_combos = 1
    for v in param_grid.values():
        total_combos *= len(v)
    
    print(f"🔍 Probando {total_combos} combinaciones de parámetros...\n")
    
    for ask in param_grid['angular_spring_k']:
        for aff in param_grid['angular_force_factor']:
            for mvf in param_grid['max_vsepr_force']:
                for sk in param_grid['spring_k']:
                    for fz in param_grid['friction_z']:
                        for ss in param_grid['symmetry_strength']:
                            params = {
                                **fixed_params,
                                'angular_spring_k': ask,
                                'angular_force_factor': aff,
                                'max_vsepr_force': mvf,
                                'spring_k': sk,
                                'friction_z': fz,
                                'symmetry_strength': ss,
                            }
                            
                            result = simulate_water(params, n_frames=1000) # Reducido a 1000 frames
                            
                            # Score: menor es mejor
                            score = (
                                result['angle_error'] * 2.0 +
                                (0 if result['stable'] else 200) +
                                max(0, 5 - result['z_spread']) * 10 +
                                (0 if result['converged'] else 100)
                            )
                            
                            if score < best_score:
                                best_score = score
                                best_params = params
                                best_result = result
    
    return best_params, best_result, best_score

def print_results(params: dict, result: dict, score: float):
    """Imprime resultados en formato legible y compacto."""
    print("--- RESULTS START ---")
    print(f"Angle: {result['final_angle']:.1f}")
    print(f"Error: {result['angle_error']:.1f}")
    print(f"Z_Spread: {result['z_spread']:.2f}")
    print(f"Max_V: {result['max_velocity']:.2f}")
    print(f"K_Angular: {params['angular_spring_k']}")
    print(f"Force_Factor: {params['angular_force_factor']}")
    print(f"Max_VSEPR: {params['max_vsepr_force']}")
    print(f"Spring_K: {params['spring_k']}")
    print(f"Friction_Z: {params['friction_z']}")
    print(f"Symmetry: {params['symmetry_strength']}")
    print("--- RESULTS END ---")

if __name__ == "__main__":
    best_params, best_result, best_score = parameter_sweep()
    print_results(best_params, best_result, best_score)
