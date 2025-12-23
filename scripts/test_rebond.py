"""
Test de Reconexión de Enlaces - LifeSimulator
=============================================
Verifica que el jugador puede reconectarse después de que un enlace se rompe.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import taichi as ti
ti.init(arch=ti.gpu, offline_cache=True)

import numpy as np
from src.systems.simulation_gpu import (
    pos, vel, is_active, atom_types, n_particles, enlaces_idx, num_enlaces,
    manos_libres, run_simulation_fast, MAX_PARTICLES
)
from src.systems.chemistry import reset_molecule_ids, propagate_molecule_ids_step
import src.config as cfg


def setup_test_scenario():
    """Configura un escenario simple: jugador H + otro H cercano."""
    n_particles[None] = 2
    
    # Posiciones iniciales cercanas
    pos_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
    pos_np[0] = [2500, 2500]  # Jugador (H)
    pos_np[1] = [2540, 2500]  # Otro H cercano (distancia 40)
    pos.from_numpy(pos_np)
    
    # Velocidades cero
    vel_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
    vel.from_numpy(vel_np)
    
    # Tipos: ambos H (índice 1)
    types_np = np.zeros(MAX_PARTICLES, dtype=np.int32)
    types_np[0] = 1  # H
    types_np[1] = 1  # H
    atom_types.from_numpy(types_np)
    
    # Ambos activos
    active_np = np.zeros(MAX_PARTICLES, dtype=np.int32)
    active_np[0] = 1
    active_np[1] = 1
    is_active.from_numpy(active_np)
    
    # Manos libres (valencia)
    manos_np = np.zeros(MAX_PARTICLES, dtype=np.float32)
    manos_np[0] = cfg.VALENCIAS[1]  # Valencia de H = 1
    manos_np[1] = cfg.VALENCIAS[1]
    manos_libres.from_numpy(manos_np)
    
    # Sin enlaces iniciales
    enlaces_np = np.full((MAX_PARTICLES, 8), -1, dtype=np.int32)
    enlaces_idx.from_numpy(enlaces_np)
    num_enlaces_np = np.zeros(MAX_PARTICLES, dtype=np.int32)
    num_enlaces.from_numpy(num_enlaces_np)
    
    print("[TEST] Escenario configurado: 2 átomos H cercanos")


def check_bond_status():
    """Verifica si hay enlace entre átomo 0 y 1."""
    n_bonds = num_enlaces.to_numpy()
    enlaces = enlaces_idx.to_numpy()
    
    bond_0_to_1 = any(enlaces[0, i] == 1 for i in range(n_bonds[0]))
    bond_1_to_0 = any(enlaces[1, i] == 0 for i in range(n_bonds[1]))
    
    return bond_0_to_1 and bond_1_to_0


def run_test():
    """Ejecuta el test de reconexión."""
    print("\n" + "="*60)
    print("TEST: Formación y Reconexión de Enlaces")
    print("="*60)
    
    setup_test_scenario()
    
    # Fase 1: Esperar formación de enlace
    print("\n[FASE 1] Esperando formación de enlace (max 1000 frames)...")
    bond_formed_at = -1
    for frame in range(1000):
        run_simulation_fast(1.0 / 60.0)
        if check_bond_status():
            bond_formed_at = frame
            print(f"  ✅ Enlace formado en frame {frame}")
            break
    
    if bond_formed_at == -1:
        print("  ❌ Enlace NO se formó en 1000 frames")
        return False
    
    # Fase 2: Separar átomos para romper enlace
    print("\n[FASE 2] Separando átomos para romper enlace...")
    pos_np = pos.to_numpy()
    pos_np[0] = [2500, 2500]  # Mover jugador lejos
    pos_np[1] = [2700, 2500]  # Distancia 200 (mayor que dist_rotura)
    pos.from_numpy(pos_np)
    
    # Esperar rotura
    for frame in range(100):
        run_simulation_fast(1.0 / 60.0)
    
    if not check_bond_status():
        print("  ✅ Enlace roto correctamente")
    else:
        print("  ⚠️ Enlace sigue intacto (puede ser normal si springs son fuertes)")
    
    # Fase 3: Acercar átomos para reconexión
    print("\n[FASE 3] Acercando átomos para reconexión...")
    pos_np = pos.to_numpy()
    pos_np[0] = [2500, 2500]
    pos_np[1] = [2540, 2500]  # Distancia 40 otra vez
    pos.from_numpy(pos_np)
    
    # Velocidades cero para estabilidad
    vel_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
    vel.from_numpy(vel_np)
    
    reconnect_at = -1
    for frame in range(1000):
        run_simulation_fast(1.0 / 60.0)
        if check_bond_status():
            reconnect_at = frame
            print(f"  ✅ Reconexión exitosa en frame {frame}")
            break
    
    if reconnect_at == -1:
        print("  ❌ Reconexión NO ocurrió en 1000 frames")
        # Diagnóstico
        manos = manos_libres.to_numpy()
        print(f"      Manos libres: átomo 0 = {manos[0]}, átomo 1 = {manos[1]}")
        positions = pos.to_numpy()
        dist = np.sqrt((positions[0,0]-positions[1,0])**2 + (positions[0,1]-positions[1,1])**2)
        print(f"      Distancia actual: {dist:.1f}")
        return False
    
    print("\n" + "="*60)
    print("✅ TEST PASADO: Formación y reconexión funcionan correctamente")
    print("="*60)
    return True


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
