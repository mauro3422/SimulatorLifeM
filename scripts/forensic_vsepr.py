"""
VSEPR Forensic Analysis - Diagnóstico de Fuerzas
=================================================
Script para analizar por qué algunas moléculas no convergen a geometría correcta.

Hipótesis a verificar:
1. Las fuerzas VSEPR son superadas por otras fuerzas
2. Los átomos no se mueven suficiente en Z
3. El symmetry breaking inicial no es suficiente
4. Las colisiones 3D interfieren con VSEPR
5. Los resortes de enlace trabajan contra VSEPR
"""

import sys
import os
import numpy as np
from collections import defaultdict

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)
print("[GPU] Taichi inicializado")

from src.systems.taichi_fields import (
    n_particles, pos, vel, is_active, atom_types, pos_z, vel_z,
    manos_libres, num_enlaces, enlaces_idx, molecule_id,
    total_bonds_count, prob_enlace_base, rango_enlace_max,
    world_width, world_height, gravity, friction, temperature,
    max_speed, dist_equilibrio, spring_k, damping,
    dist_rotura, max_fuerza, radii
)
from src.config import system_constants as sys_cfg
from src.systems.simulation_gpu import simulation_step_gpu
from src.systems.chemistry_constants import ANGULAR_SPRING_K, ANGULAR_FORCE_FACTOR

ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']
VALENCIAS = [4, 1, 3, 2, 5, 2]

# Ángulos ideales
IDEAL_ANGLES = {
    (3, 2): 104.5,  # O con 2 enlaces (agua)
    (2, 3): 107.0,  # N con 3 enlaces
    (0, 4): 109.5,  # C con 4 enlaces
}


def initialize_simulation(n_part: int = 1000, spawn_area: float = 300.0):
    """Inicializa simulación pequeña para análisis detallado."""
    print(f"\n[INIT] Configurando {n_part} partículas para análisis...")
    
    n_particles[None] = n_part
    
    center = sys_cfg.WORLD_SIZE / 2.0
    pos_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_data[:n_part] = (np.random.rand(n_part, 2) * spawn_area) + (center - spawn_area / 2.0)
    pos.from_numpy(pos_data)
    
    vel_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    vel_data[:n_part] = (np.random.rand(n_part, 2) - 0.5) * 5.0
    vel.from_numpy(vel_data)
    
    # Inicializar pos_z con pequeña variación para romper simetría
    pos_z_data = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    pos_z_data[:n_part] = (np.random.rand(n_part) - 0.5) * 5.0  # ±2.5 inicial
    pos_z.from_numpy(pos_z_data)
    
    vel_z_data = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    vel_z.from_numpy(vel_z_data)
    
    is_active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    is_active_np[:n_part] = 1
    is_active.from_numpy(is_active_np)
    
    # Alta proporción de H y O para formar agua
    probs = [0.10, 0.60, 0.10, 0.15, 0.02, 0.03]
    atom_types_data = np.random.choice(6, size=sys_cfg.MAX_PARTICLES, p=probs).astype(np.int32)
    atom_types.from_numpy(atom_types_data)
    
    manos_data = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.float32)
    for i in range(n_part):
        t = atom_types_data[i]
        manos_data[i] = float(VALENCIAS[t])
    manos_libres.from_numpy(manos_data)
    
    mol_id_data = np.arange(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    molecule_id.from_numpy(mol_id_data)
    
    num_enlaces.fill(0)
    enlaces_idx.fill(-1)
    total_bonds_count[None] = 0
    
    world_width[None] = sys_cfg.WORLD_SIZE
    world_height[None] = sys_cfg.WORLD_SIZE
    gravity[None] = 0.0
    friction[None] = 0.95
    temperature[None] = 0.05
    max_speed[None] = sys_cfg.MAX_SPEED
    
    prob_enlace_base[None] = 0.3
    rango_enlace_max[None] = 210.0
    dist_equilibrio[None] = sys_cfg.DIST_EQUILIBRIO
    spring_k[None] = 0.5
    damping[None] = 0.8
    dist_rotura[None] = sys_cfg.DIST_ROTURA
    max_fuerza[None] = sys_cfg.MAX_FORCE
    
    return n_part


def find_water_molecules(n_part):
    """Encuentra moléculas de agua (H2O) en la simulación."""
    num_enlaces_np = num_enlaces.to_numpy()[:n_part]
    atom_types_np = atom_types.to_numpy()[:n_part]
    mol_ids_np = molecule_id.to_numpy()[:n_part]
    is_active_np = is_active.to_numpy()[:n_part]
    enlaces_idx_np = enlaces_idx.to_numpy()[:n_part]
    
    water_molecules = []
    
    for i in range(n_part):
        if is_active_np[i] and atom_types_np[i] == 3 and num_enlaces_np[i] == 2:
            # i es un Oxígeno con 2 enlaces - posible agua
            neighbors = []
            for b in range(num_enlaces_np[i]):
                j = enlaces_idx_np[i, b]
                if j >= 0 and atom_types_np[j] == 1:  # H
                    neighbors.append(j)
            
            if len(neighbors) == 2:
                water_molecules.append({
                    'O': i,
                    'H1': neighbors[0],
                    'H2': neighbors[1]
                })
    
    return water_molecules


def analyze_molecule_forces(mol_indices, n_part):
    """Analiza las fuerzas y geometría de una molécula específica."""
    pos_np = pos.to_numpy()[:n_part]
    pos_z_np = pos_z.to_numpy()[:n_part]
    vel_np = vel.to_numpy()[:n_part]
    vel_z_np = vel_z.to_numpy()[:n_part]
    radii_np = radii.to_numpy()[:n_part]
    
    O, H1, H2 = mol_indices['O'], mol_indices['H1'], mol_indices['H2']
    
    # Posiciones 3D
    pos_O = np.array([pos_np[O, 0], pos_np[O, 1], pos_z_np[O]])
    pos_H1 = np.array([pos_np[H1, 0], pos_np[H1, 1], pos_z_np[H1]])
    pos_H2 = np.array([pos_np[H2, 0], pos_np[H2, 1], pos_z_np[H2]])
    
    # Vectores de enlace
    v1 = pos_H1 - pos_O
    v2 = pos_H2 - pos_O
    
    # Distancias de enlace
    d1 = np.linalg.norm(v1)
    d2 = np.linalg.norm(v2)
    
    # Ángulo 3D
    if d1 > 0.001 and d2 > 0.001:
        cos_angle = np.clip(np.dot(v1, v2) / (d1 * d2), -1, 1)
        angle_deg = np.degrees(np.arccos(cos_angle))
    else:
        angle_deg = 0.0
    
    # Velocidades
    vel_O = np.array([vel_np[O, 0], vel_np[O, 1], vel_z_np[O]])
    vel_H1 = np.array([vel_np[H1, 0], vel_np[H1, 1], vel_z_np[H1]])
    vel_H2 = np.array([vel_np[H2, 0], vel_np[H2, 1], vel_z_np[H2]])
    
    # Análisis Z específico
    z_O, z_H1, z_H2 = pos_z_np[O], pos_z_np[H1], pos_z_np[H2]
    vz_O, vz_H1, vz_H2 = vel_z_np[O], vel_z_np[H1], vel_z_np[H2]
    
    return {
        'angle': angle_deg,
        'bond_lengths': (d1, d2),
        'z_positions': (z_O, z_H1, z_H2),
        'z_velocities': (vz_O, vz_H1, vz_H2),
        'xy_velocities': (np.linalg.norm(vel_O[:2]), np.linalg.norm(vel_H1[:2]), np.linalg.norm(vel_H2[:2])),
        'total_z_spread': max(z_O, z_H1, z_H2) - min(z_O, z_H1, z_H2),
        'radii': (radii_np[O], radii_np[H1], radii_np[H2])
    }


def calculate_expected_vsepr_force(angle_deg, ideal_angle=104.5):
    """Calcula la fuerza VSEPR esperada dado el ángulo actual."""
    angle_rad = np.radians(angle_deg)
    ideal_rad = np.radians(ideal_angle)
    
    angle_diff = angle_rad - ideal_rad
    torque = angle_diff * ANGULAR_SPRING_K
    force_mag = torque * ANGULAR_FORCE_FACTOR
    
    return {
        'angle_diff_rad': angle_diff,
        'angle_diff_deg': np.degrees(angle_diff),
        'expected_force_mag': abs(force_mag),
        'direction': 'expand' if angle_diff < 0 else 'contract'
    }


def run_forensic_analysis():
    """Ejecuta análisis forense completo."""
    print("\n" + "="*70)
    print("🔍 ANÁLISIS FORENSE VSEPR - LifeSimulator")
    print("="*70)
    
    n_part = initialize_simulation(n_part=1000, spawn_area=300.0)
    
    # Ejecutar simulación inicial para formar moléculas
    print("\n[FASE 1] Formando moléculas (500 frames)...")
    for frame in range(500):
        simulation_step_gpu(1)
        ti.sync()
    
    bonds = total_bonds_count[None]
    print(f"   Enlaces formados: {bonds}")
    
    # Encontrar moléculas de agua
    water_mols = find_water_molecules(n_part)
    print(f"\n[FASE 2] Moléculas de agua encontradas: {len(water_mols)}")
    
    if len(water_mols) == 0:
        print("   ⚠️ No se encontraron moléculas de agua para analizar")
        return
    
    # Tomar las primeras 5 moléculas de agua para análisis detallado
    target_mols = water_mols[:5]
    
    print(f"\n[FASE 3] Analizando {len(target_mols)} moléculas de agua...")
    print("-"*70)
    
    # Análisis inicial
    print("\n📊 ESTADO INICIAL (después de formación):")
    for i, mol in enumerate(target_mols):
        analysis = analyze_molecule_forces(mol, n_part)
        vsepr_expected = calculate_expected_vsepr_force(analysis['angle'])
        
        print(f"\n   H2O #{i+1} (O={mol['O']}, H1={mol['H1']}, H2={mol['H2']}):")
        print(f"      Ángulo: {analysis['angle']:.1f}° (ideal: 104.5°)")
        print(f"      Bond lengths: {analysis['bond_lengths'][0]:.1f}, {analysis['bond_lengths'][1]:.1f}")
        print(f"      Z spread: {analysis['total_z_spread']:.2f}")
        print(f"      Z positions: O={analysis['z_positions'][0]:.2f}, H1={analysis['z_positions'][1]:.2f}, H2={analysis['z_positions'][2]:.2f}")
        print(f"      Z velocities: O={analysis['z_velocities'][0]:.4f}, H1={analysis['z_velocities'][1]:.4f}, H2={analysis['z_velocities'][2]:.4f}")
        print(f"      VSEPR force expected: {vsepr_expected['expected_force_mag']:.4f} ({vsepr_expected['direction']})")
    
    # Ejecutar más frames y trackear evolución
    print(f"\n[FASE 4] Tracking evolución (1500 frames adicionales)...")
    
    angle_history = {i: [] for i in range(len(target_mols))}
    z_spread_history = {i: [] for i in range(len(target_mols))}
    
    for frame in range(1500):
        simulation_step_gpu(1)
        ti.sync()
        
        if frame % 100 == 0:
            for i, mol in enumerate(target_mols):
                analysis = analyze_molecule_forces(mol, n_part)
                angle_history[i].append(analysis['angle'])
                z_spread_history[i].append(analysis['total_z_spread'])
    
    print("\n📈 EVOLUCIÓN DE ÁNGULOS:")
    print("-"*70)
    print(f"{'Mol':5s} | {'Inicial':8s} | {'Frame 500':10s} | {'Frame 1000':10s} | {'Final':8s} | {'Trend':10s}")
    print("-"*70)
    
    for i in range(len(target_mols)):
        angles = angle_history[i]
        if len(angles) >= 4:
            initial = angles[0]
            mid1 = angles[len(angles)//3]
            mid2 = angles[2*len(angles)//3]
            final = angles[-1]
            trend = "📈 subiendo" if final > initial + 5 else "📉 bajando" if final < initial - 5 else "➡️ estable"
            print(f"  #{i+1:2d} | {initial:6.1f}° | {mid1:8.1f}° | {mid2:9.1f}° | {final:6.1f}° | {trend}")
    
    # Análisis final
    print(f"\n[FASE 5] ANÁLISIS FINAL:")
    print("="*70)
    
    for i, mol in enumerate(target_mols):
        analysis = analyze_molecule_forces(mol, n_part)
        vsepr_expected = calculate_expected_vsepr_force(analysis['angle'])
        
        print(f"\n   H2O #{i+1}:")
        print(f"      Ángulo final: {analysis['angle']:.1f}° (error: {abs(104.5 - analysis['angle']):.1f}°)")
        print(f"      Z spread final: {analysis['total_z_spread']:.2f}")
        print(f"      Z velocities: {analysis['z_velocities']}")
    
    # Diagnóstico
    print("\n" + "="*70)
    print("🩺 DIAGNÓSTICO:")
    print("="*70)
    
    avg_final_angle = np.mean([angle_history[i][-1] for i in range(len(target_mols)) if angle_history[i]])
    avg_z_spread = np.mean([z_spread_history[i][-1] for i in range(len(target_mols)) if z_spread_history[i]])
    
    print(f"\n   Ángulo promedio final: {avg_final_angle:.1f}° (objetivo: 104.5°)")
    print(f"   Z spread promedio: {avg_z_spread:.2f}")
    
    if avg_z_spread < 5.0:
        print("\n   ⚠️ PROBLEMA: Z spread muy bajo - los átomos están muy planos")
        print("      CAUSA PROBABLE: Symmetry breaking insuficiente o fuerzas Z muy débiles")
    
    if avg_final_angle < 90:
        print("\n   ⚠️ PROBLEMA: Ángulos demasiado pequeños")
        print("      CAUSA PROBABLE: Bond springs empujan átomos hacia dentro")
    
    # Calcular ratio de fuerza VSEPR vs equilibrio
    print(f"\n   📐 ANÁLISIS DE FUERZAS:")
    print(f"      ANGULAR_SPRING_K = {ANGULAR_SPRING_K}")
    print(f"      ANGULAR_FORCE_FACTOR = {ANGULAR_FORCE_FACTOR}")
    print(f"      spring_k (bonds) = {spring_k[None]}")
    print(f"      dist_equilibrio = {dist_equilibrio[None]}")
    
    # Para ángulo de 80° cuando debería ser 104.5°:
    # Diferencia: 24.5° = 0.43 rad
    # Fuerza VSEPR = 0.43 * 8.0 * 3.0 = 10.3
    vsepr_force_80 = abs(np.radians(104.5 - 80)) * ANGULAR_SPRING_K * ANGULAR_FORCE_FACTOR
    print(f"\n      Fuerza VSEPR para ángulo 80°: {vsepr_force_80:.2f}")
    print(f"      (Si los átomos no se mueven, esta fuerza es insuficiente o contrarrestada)")


if __name__ == "__main__":
    run_forensic_analysis()
