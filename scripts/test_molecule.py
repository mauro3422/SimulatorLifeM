"""
Test Molecule Formation - Verificar si moléculas específicas pueden formarse
==============================================================================
Uso:
    python scripts/test_molecule.py --target "C5H5N5"  # Test Adenina
    python scripts/test_molecule.py --target "C5H5N5O1" --atoms "C,H,N,O"  # Con átomos específicos
    python scripts/test_molecule.py --nucleobases  # Test todas las bases del ADN
"""

import sys
import os
import argparse
import time
import numpy as np

# Fix path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

import taichi as ti
ti.init(arch=ti.vulkan, offline_cache=True)

from src.systems.taichi_fields import (
    n_particles, pos, pos_z, vel, vel_z, atom_types, num_enlaces, enlaces_idx,
    molecule_id, is_active, total_bonds_count, radii, manos_libres,
    MASAS_ATOMICAS, temperature, prob_enlace_base, dist_equilibrio,
    spring_k, damping, dist_rotura, max_fuerza, rango_enlace_max, sim_bounds
)
from src.systems.simulation_gpu import simulation_step_gpu, init_molecule_ids
from src.systems.molecule_detector import get_molecule_detector
from src.config import system_constants as cfg
from src.config.molecules import get_molecule_name, is_known_molecule

# Colores
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Mapeo de símbolos a tipos
ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']


def setup_atoms_for_target(target_formula: str, n_atoms: int = 500):
    """
    Configura los átomos correctos para intentar formar la molécula objetivo.
    Parsea la fórmula y crea proporciones correctas.
    """
    # Parsear fórmula (ej: C5H5N5 -> {C:5, H:5, N:5})
    import re
    parts = re.findall(r'([A-Z][a-z]?)(\d*)', target_formula)
    counts = {}
    for symbol, count in parts:
        if symbol:
            counts[symbol] = int(count) if count else 1
    
    total_in_formula = sum(counts.values())
    
    # Calcular cuántas copias de la fórmula podemos hacer
    copies = n_atoms // total_in_formula
    
    print(f"[SETUP] Fórmula objetivo: {target_formula}")
    print(f"[SETUP] Composición: {counts}")
    print(f"[SETUP] Creando ~{copies} copias potenciales")
    
    # Inicializar campos
    n_particles[None] = n_atoms
    temperature[None] = 0.7  # Alta temperatura para más reacciones
    prob_enlace_base[None] = 0.25  # Alta probabilidad de enlace
    dist_equilibrio[None] = 80.0
    spring_k[None] = 0.002
    damping[None] = 0.0004
    dist_rotura[None] = 150.0
    max_fuerza[None] = 80.0
    rango_enlace_max[None] = 120.0
    
    # Crear arrays
    pos_np = np.zeros((cfg.MAX_PARTICLES, 2), dtype=np.float32)
    posZ_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.float32)
    vel_np = np.zeros((cfg.MAX_PARTICLES, 2), dtype=np.float32)
    types_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.int32)
    active_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.int32)
    radii_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.float32)
    manos_np = np.zeros(cfg.MAX_PARTICLES, dtype=np.float32)
    
    # Distribuir átomos según la fórmula
    center = cfg.WORLD_SIZE / 2
    atom_idx = 0
    
    for copy in range(copies):
        # Posición del grupo (cluster)
        cluster_x = center + (np.random.rand() - 0.5) * 400
        cluster_y = center + (np.random.rand() - 0.5) * 400
        
        for symbol, count in counts.items():
            if symbol not in ATOM_SYMBOLS:
                print(f"[WARN] Átomo '{symbol}' no soportado, saltando")
                continue
                
            type_id = ATOM_SYMBOLS.index(symbol)
            
            for _ in range(count):
                if atom_idx >= n_atoms:
                    break
                    
                # Posición cercana al cluster
                pos_np[atom_idx] = [
                    cluster_x + (np.random.rand() - 0.5) * 60,
                    cluster_y + (np.random.rand() - 0.5) * 60
                ]
                types_np[atom_idx] = type_id
                active_np[atom_idx] = 1
                radii_np[atom_idx] = MASAS_ATOMICAS[type_id] * 3 + 8
                manos_np[atom_idx] = 2.0 if type_id != 1 else 1.0  # H tiene 1 mano
                atom_idx += 1
    
    # Subir a GPU
    pos.from_numpy(pos_np)
    pos_z.from_numpy(posZ_np)
    vel.from_numpy(vel_np)
    vel_z.from_numpy(posZ_np.copy())
    atom_types.from_numpy(types_np)
    is_active.from_numpy(active_np)
    radii.from_numpy(radii_np)
    manos_libres.from_numpy(manos_np)
    
    # Bounds
    sim_bounds[0] = 0
    sim_bounds[1] = cfg.WORLD_SIZE
    sim_bounds[2] = 0
    sim_bounds[3] = cfg.WORLD_SIZE
    
    init_molecule_ids()
    ti.sync()
    
    return atom_idx


def run_test(target_formula: str, max_frames: int = 2000, check_interval: int = 100):
    """Ejecuta la simulación y busca la molécula objetivo."""
    
    detector = get_molecule_detector()
    found_target = False
    found_at_frame = 0
    
    print(f"\n{BOLD}🧪 TEST: Intentando formar {target_formula}{RESET}")
    name = get_molecule_name(target_formula)
    print(f"   Nombre: {name}")
    print(f"   Frames máximos: {max_frames}")
    print("-" * 50)
    
    start_time = time.time()
    
    for frame in range(1, max_frames + 1):
        simulation_step_gpu(1)
        
        if frame % check_interval == 0:
            ti.sync()
            
            # Detectar moléculas
            detector.detect_molecules(
                atom_types.to_numpy(),
                None,
                num_enlaces.to_numpy(),
                molecule_id,
                n_particles[None]
            )
            
            formulas = detector.stats['last_scan_formulas']
            
            # Buscar objetivo
            if target_formula in formulas:
                found_target = True
                found_at_frame = frame
                count = formulas[target_formula]
                print(f"   ✅ ¡ENCONTRADA! {target_formula} x{count} en frame {frame}")
                break
            
            # Mostrar progreso
            total = sum(formulas.values())
            known = sum(c for f, c in formulas.items() if is_known_molecule(f))
            print(f"   [{frame}/{max_frames}] Moléculas: {total} total, {known} conocidas, bonds={total_bonds_count[None]}")
    
    elapsed = time.time() - start_time
    
    print("-" * 50)
    if found_target:
        print(f"{GREEN}{BOLD}✅ ÉXITO: {target_formula} se formó en frame {found_at_frame}{RESET}")
    else:
        print(f"{RED}{BOLD}❌ NO ENCONTRADA: {target_formula} no apareció en {max_frames} frames{RESET}")
        
        # Mostrar qué sí se formó
        print(f"\n{YELLOW}Moléculas conocidas que SÍ se formaron:{RESET}")
        for formula, count in sorted(detector.stats['last_scan_formulas'].items()):
            name = get_molecule_name(formula)
            if name != "Transitorio":
                print(f"   {formula} ({name}): {count}")
    
    print(f"\nTiempo: {elapsed:.1f}s")
    return found_target


def test_nucleobases():
    """Test específico para las 4 bases del ADN/ARN."""
    bases = {
        "C5H5N5": "Adenina (A)",
        "C5H5N5O1": "Guanina (G)",
        "C4H5N3O1": "Citosina (C)",
        "C5H6N2O2": "Timina (T)",
        "C4H4N2O2": "Uracilo (U) - ARN"
    }
    
    print(f"\n{BOLD}{CYAN}🧬 TEST DE NUCLEOBASES (A, G, C, T, U){RESET}")
    print("=" * 60)
    
    results = {}
    for formula, name in bases.items():
        print(f"\n--- Testing {name} ({formula}) ---")
        setup_atoms_for_target(formula, n_atoms=800)
        found = run_test(formula, max_frames=3000, check_interval=200)
        results[formula] = found
    
    print("\n" + "=" * 60)
    print(f"{BOLD}RESUMEN:{RESET}")
    for formula, name in bases.items():
        status = f"{GREEN}✅{RESET}" if results.get(formula) else f"{RED}❌{RESET}"
        print(f"  {status} {name}: {formula}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test de formación de moléculas")
    parser.add_argument("--target", type=str, help="Fórmula objetivo (ej: C5H5N5)")
    parser.add_argument("--nucleobases", action="store_true", help="Test las 4 bases A,G,C,T,U")
    parser.add_argument("--frames", type=int, default=2000, help="Frames máximos")
    parser.add_argument("--atoms", type=int, default=500, help="Número de átomos")
    args = parser.parse_args()
    
    if args.nucleobases:
        test_nucleobases()
    elif args.target:
        setup_atoms_for_target(args.target, args.atoms)
        run_test(args.target, args.frames)
    else:
        print("Uso: python scripts/test_molecule.py --target C5H5N5")
        print("     python scripts/test_molecule.py --nucleobases")
