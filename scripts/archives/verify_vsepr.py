"""
VSEPR Geometry Verification - Verificación de Geometría Molecular
===================================================================
Verifica que las moléculas se formen con los ángulos correctos según VSEPR.

Ángulos teóricos:
- H2O (agua): 104.5° (2 enlaces + 2 pares solitarios)
- NH3 (amoníaco): 107° (3 enlaces + 1 par solitario)  
- CH4 (metano): 109.5° (4 enlaces, tetraédrico)
- CO2 (dióxido de carbono): 180° (lineal)
- BF3 / trigonal: 120° (trigonal plana)
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
    dist_rotura, max_fuerza
)
from src.config import system_constants as sys_cfg
from src.systems.simulation_gpu import simulation_step_gpu
from src.config.molecules import get_molecule_name

ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']
VALENCIAS = [4, 1, 3, 2, 5, 2]

# Ángulos teóricos VSEPR
IDEAL_ANGLES = {
    'H2O': 104.5,   # Agua - angular
    'H2O1': 104.5,  # Variante
    'O1H2': 104.5,  # Variante
    'NH3': 107.0,   # Amoníaco - piramidal
    'H3N1': 107.0,
    'CH4': 109.5,   # Metano - tetraédrico
    'H4C1': 109.5,
    'C1H4': 109.5,
    'CO2': 180.0,   # Dióxido de carbono - lineal
    'C1O2': 180.0,
    'H2': None,     # Solo 1 enlace, no aplica
    'O2': None,     # Solo 1 enlace, no aplica
}

# Ángulos esperados por tipo de átomo central y número de enlaces
EXPECTED_BY_TYPE = {
    (3, 2): 104.5,  # O con 2 enlaces (agua)
    (2, 3): 107.0,  # N con 3 enlaces (amoníaco)
    (0, 4): 109.5,  # C con 4 enlaces (metano)
    (0, 3): 120.0,  # C con 3 enlaces (trigonal)
    (0, 2): 180.0,  # C con 2 enlaces (lineal)
}


def initialize_simulation(n_part: int = 3000, spawn_area: float = 500.0):
    """Inicializa simulación con foco en moléculas pequeñas."""
    print(f"\n[INIT] Configurando {n_part} partículas...")
    
    n_particles[None] = n_part
    
    center = sys_cfg.WORLD_SIZE / 2.0
    pos_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    pos_data[:n_part] = (np.random.rand(n_part, 2) * spawn_area) + (center - spawn_area / 2.0)
    pos.from_numpy(pos_data)
    
    vel_data = np.zeros((sys_cfg.MAX_PARTICLES, 2), dtype=np.float32)
    vel_data[:n_part] = (np.random.rand(n_part, 2) - 0.5) * 10.0
    vel.from_numpy(vel_data)
    
    is_active_np = np.zeros(sys_cfg.MAX_PARTICLES, dtype=np.int32)
    is_active_np[:n_part] = 1
    is_active.from_numpy(is_active_np)
    
    # Alta proporción de H y O para formar agua
    probs = [0.15, 0.55, 0.10, 0.15, 0.02, 0.03]
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
    temperature[None] = 0.1
    max_speed[None] = sys_cfg.MAX_SPEED
    
    prob_enlace_base[None] = 0.3
    rango_enlace_max[None] = 210.0
    dist_equilibrio[None] = sys_cfg.DIST_EQUILIBRIO
    spring_k[None] = 0.5
    damping[None] = 0.8
    dist_rotura[None] = sys_cfg.DIST_ROTURA
    max_fuerza[None] = sys_cfg.MAX_FORCE
    
    return n_part


def measure_molecule_angles(indices, pos_np, pos_z_np, atom_types_np, enlaces_idx_np, num_enlaces_np):
    """Mide todos los ángulos de una molécula específica en 3D."""
    angles_by_center = defaultdict(list)
    
    for i in indices:
        n_bonds = num_enlaces_np[i]
        if n_bonds >= 2:
            atom_type = atom_types_np[i]
            # Posición 3D del centro
            p_center_x = pos_np[i, 0]
            p_center_y = pos_np[i, 1]
            p_center_z = pos_z_np[i]
            neighbors = []
            
            for b in range(n_bonds):
                j = enlaces_idx_np[i, b]
                if j >= 0:
                    neighbors.append(j)
            
            # Calcular ángulos entre todos los pares de vecinos en 3D
            for a in range(len(neighbors)):
                for b in range(a + 1, len(neighbors)):
                    j1, j2 = neighbors[a], neighbors[b]
                    # Vectores 3D desde el centro a los vecinos
                    v1 = np.array([
                        pos_np[j1, 0] - p_center_x,
                        pos_np[j1, 1] - p_center_y,
                        pos_z_np[j1] - p_center_z
                    ])
                    v2 = np.array([
                        pos_np[j2, 0] - p_center_x,
                        pos_np[j2, 1] - p_center_y,
                        pos_z_np[j2] - p_center_z
                    ])
                    
                    len1 = np.linalg.norm(v1)
                    len2 = np.linalg.norm(v2)
                    
                    if len1 > 0.001 and len2 > 0.001:
                        cos_angle = np.clip(np.dot(v1, v2) / (len1 * len2), -1.0, 1.0)
                        angle_deg = np.degrees(np.arccos(cos_angle))
                        angles_by_center[(ATOM_SYMBOLS[atom_type], n_bonds)].append(angle_deg)
    
    return angles_by_center


def verify_vsepr_geometry(n_part):
    """Verifica que la geometría VSEPR sea correcta."""
    print("\n" + "="*70)
    print("📐 VERIFICACIÓN DE GEOMETRÍA MOLECULAR VSEPR")
    print("="*70)
    
    # Get data
    num_enlaces_np = num_enlaces.to_numpy()[:n_part]
    atom_types_np = atom_types.to_numpy()[:n_part]
    enlaces_idx_np = enlaces_idx.to_numpy()[:n_part]
    is_active_np = is_active.to_numpy()[:n_part]
    mol_ids_np = molecule_id.to_numpy()[:n_part]
    pos_np = pos.to_numpy()[:n_part]
    pos_z_np = pos_z.to_numpy()[:n_part]
    
    # Detectar moléculas conocidas
    mol_groups = defaultdict(list)
    for i in range(n_part):
        if is_active_np[i] and num_enlaces_np[i] > 0:
            mid = mol_ids_np[i]
            if mid >= 0:
                mol_groups[mid].append(i)
    
    # Clasificar moléculas por fórmula
    molecules_by_formula = defaultdict(list)
    
    for mid, indices in mol_groups.items():
        if len(indices) >= 2:
            atom_counts = defaultdict(int)
            for idx in indices:
                t = atom_types_np[idx]
                if 0 <= t < len(ATOM_SYMBOLS):
                    atom_counts[ATOM_SYMBOLS[t]] += 1
            
            parts = []
            if 'C' in atom_counts: parts.append(f"C{atom_counts.pop('C')}")
            if 'H' in atom_counts: parts.append(f"H{atom_counts.pop('H')}")
            for s in sorted(atom_counts.keys()): 
                parts.append(f"{s}{atom_counts[s]}")
            formula = "".join(parts)
            
            molecules_by_formula[formula].append(indices)
    
    # Analizar ángulos por fórmula conocida
    print("\n📊 ÁNGULOS POR FÓRMULA MOLECULAR:")
    print("-"*70)
    print(f"{'Fórmula':12s} | {'Nombre':15s} | {'N':4s} | {'Ángulo Real':12s} | {'Ideal':8s} | {'Error':8s}")
    print("-"*70)
    
    results = []
    
    for formula, mol_list in sorted(molecules_by_formula.items(), key=lambda x: -len(x[1])):
        if len(mol_list) < 3:  # Need at least 3 samples
            continue
            
        all_angles = []
        for indices in mol_list[:50]:  # Max 50 samples
            angles = measure_molecule_angles(
                indices, pos_np, pos_z_np, atom_types_np, enlaces_idx_np, num_enlaces_np
            )
            for (center_type, n_bonds), angle_list in angles.items():
                all_angles.extend(angle_list)
        
        if not all_angles:
            continue
            
        avg_angle = np.mean(all_angles)
        std_angle = np.std(all_angles)
        name = get_molecule_name(formula)
        
        # Buscar ángulo ideal
        ideal = IDEAL_ANGLES.get(formula)
        if ideal is None:
            # Intentar por tipo de átomo central
            for indices in mol_list[:1]:
                for i in indices:
                    t = atom_types_np[i]
                    n = num_enlaces_np[i]
                    if (t, n) in EXPECTED_BY_TYPE:
                        ideal = EXPECTED_BY_TYPE[(t, n)]
                        break
        
        if ideal:
            error = abs(avg_angle - ideal)
            error_str = f"{error:+.1f}°"
            ideal_str = f"{ideal:.1f}°"
        else:
            error = None
            error_str = "N/A"
            ideal_str = "N/A"
        
        print(f"{formula:12s} | {name:15s} | {len(mol_list):4d} | {avg_angle:.1f}° ±{std_angle:.1f}° | {ideal_str:8s} | {error_str:8s}")
        
        results.append({
            'formula': formula,
            'name': name,
            'count': len(mol_list),
            'avg_angle': avg_angle,
            'std_angle': std_angle,
            'ideal': ideal,
            'error': error
        })
    
    # Análisis por tipo de átomo central
    print("\n📊 ÁNGULOS POR TIPO DE ÁTOMO CENTRAL:")
    print("-"*70)
    
    all_angles_by_type = defaultdict(list)
    
    for mid, indices in mol_groups.items():
        angles = measure_molecule_angles(
            indices, pos_np, pos_z_np, atom_types_np, enlaces_idx_np, num_enlaces_np
        )
        for key, angle_list in angles.items():
            all_angles_by_type[key].extend(angle_list)
    
    print(f"{'Tipo':8s} | {'#Bonds':6s} | {'Samples':8s} | {'Ángulo Real':12s} | {'Ideal':8s} | {'Error':8s} | {'Estado':10s}")
    print("-"*70)
    
    for (center_type, n_bonds), angles in sorted(all_angles_by_type.items()):
        if len(angles) < 10:
            continue
            
        avg = np.mean(angles)
        std = np.std(angles)
        
        # Buscar ideal
        type_idx = ATOM_SYMBOLS.index(center_type)
        ideal = EXPECTED_BY_TYPE.get((type_idx, n_bonds))
        
        if ideal:
            error = abs(avg - ideal)
            status = "✅ OK" if error < 15 else "⚠️ REVISAR" if error < 30 else "❌ MAL"
            ideal_str = f"{ideal:.1f}°"
            error_str = f"{error:+.1f}°"
        else:
            status = "?"
            ideal_str = "N/A"
            error_str = "N/A"
        
        print(f"{center_type:8s} | {n_bonds:6d} | {len(angles):8d} | {avg:.1f}° ±{std:.1f}° | {ideal_str:8s} | {error_str:8s} | {status:10s}")
    
    # Resumen final
    print("\n" + "="*70)
    print("📋 CONCLUSIONES")
    print("="*70)
    
    # Calcular métricas globales
    good_results = [r for r in results if r['error'] is not None and r['error'] < 15]
    ok_results = [r for r in results if r['error'] is not None and 15 <= r['error'] < 30]
    bad_results = [r for r in results if r['error'] is not None and r['error'] >= 30]
    
    print(f"\n   Moléculas con geometría CORRECTA (<15° error): {len(good_results)}")
    print(f"   Moléculas con geometría ACEPTABLE (15-30° error): {len(ok_results)}")
    print(f"   Moléculas con geometría INCORRECTA (>30° error): {len(bad_results)}")
    
    if bad_results:
        print(f"\n   ⚠️  Moléculas problemáticas:")
        for r in bad_results[:5]:
            print(f"      - {r['formula']}: {r['avg_angle']:.1f}° (debería ser {r['ideal']:.1f}°)")
    
    # Diagnóstico
    print("\n🩺 DIAGNÓSTICO:")
    
    # Verificar H2O específicamente
    h2o_result = next((r for r in results if 'H2' in r['formula'] and 'O' in r['formula'] and r['count'] > 5), None)
    if h2o_result:
        if h2o_result['error'] and h2o_result['error'] < 15:
            print(f"   ✅ Agua (H2O): Geometría angular correcta ({h2o_result['avg_angle']:.1f}°)")
        else:
            print(f"   ⚠️ Agua (H2O): Ángulo {h2o_result['avg_angle']:.1f}° (debería ser ~104.5°)")
    
    # Verificar metano CH4
    ch4_result = next((r for r in results if r['formula'] == 'C1H4' or r['formula'] == 'CH4'), None)
    if ch4_result:
        if ch4_result['error'] and ch4_result['error'] < 15:
            print(f"   ✅ Metano (CH4): Geometría tetraédrica correcta ({ch4_result['avg_angle']:.1f}°)")
        else:
            print(f"   ⚠️ Metano (CH4): Ángulo {ch4_result['avg_angle']:.1f}° (debería ser ~109.5°)")


def main():
    print("\n" + "="*70)
    print("🔬 VERIFICACIÓN DE GEOMETRÍA VSEPR - LifeSimulator")
    print("="*70)
    
    n_part = initialize_simulation(n_part=3000, spawn_area=500.0)
    
    print(f"\n[SIM] Ejecutando 2000 frames para estabilizar geometría...")
    print(f"      Midiendo ángulos cada 500 frames para ver convergencia...")
    
    for frame in range(2000):
        simulation_step_gpu(1)
        ti.sync()
        
        # Medir ángulos periódicamente (cada 500 frames)
        if frame % 500 == 499:
            bonds = total_bonds_count[None]
            # Quick angle measurement
            pos_np = pos.to_numpy()[:n_part]
            pos_z_np = pos_z.to_numpy()[:n_part]
            vel_z_np = vel_z.to_numpy()[:n_part]
            vel_np = vel.to_numpy()[:n_part]
            num_enlaces_np = num_enlaces.to_numpy()[:n_part]
            enlaces_idx_np = enlaces_idx.to_numpy()[:n_part]
            is_active_np = is_active.to_numpy()[:n_part]
            
            # Debug: Z movement statistics
            bonded_mask = num_enlaces_np > 0
            if bonded_mask.sum() > 0:
                z_range = pos_z_np[bonded_mask].max() - pos_z_np[bonded_mask].min()
                z_std = pos_z_np[bonded_mask].std()
                vel_z_rms = np.sqrt((vel_z_np[bonded_mask]**2).mean())
                vel_xy_rms = np.sqrt((vel_np[bonded_mask]**2).sum(axis=1).mean())
            else:
                z_range = z_std = vel_z_rms = vel_xy_rms = 0.0
            
            angles = []
            for i in range(n_part):
                if num_enlaces_np[i] >= 2:
                    neighbors = [enlaces_idx_np[i,b] for b in range(num_enlaces_np[i]) if enlaces_idx_np[i,b] >= 0]
                    cx, cy, cz = pos_np[i,0], pos_np[i,1], pos_z_np[i]
                    for a in range(len(neighbors)):
                        for b in range(a+1, len(neighbors)):
                            j1, j2 = neighbors[a], neighbors[b]
                            v1 = np.array([pos_np[j1,0]-cx, pos_np[j1,1]-cy, pos_z_np[j1]-cz])
                            v2 = np.array([pos_np[j2,0]-cx, pos_np[j2,1]-cy, pos_z_np[j2]-cz])
                            l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
                            if l1 > 0.001 and l2 > 0.001:
                                cos_a = np.clip(np.dot(v1,v2)/(l1*l2), -1, 1)
                                angles.append(np.degrees(np.arccos(cos_a)))
            
            if angles:
                avg_angle = np.mean(angles)
                print(f"   Frame {frame+1}: {bonds} enlaces, avg_angle={avg_angle:.1f}°")
                print(f"      Z_range={z_range:.1f}, Z_std={z_std:.2f}, vel_z_rms={vel_z_rms:.3f}, vel_xy_rms={vel_xy_rms:.3f}")
    
    verify_vsepr_geometry(n_part)
    
    print("\n" + "="*70)
    print("✅ Verificación completada")
    print("="*70)


if __name__ == "__main__":
    main()
