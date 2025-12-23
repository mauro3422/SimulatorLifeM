"""
Detector de Moleculas - QuimicPYTHON
=====================================
Detecta moleculas conocidas en la simulacion y genera eventos.
"""
import numpy as np
from src.core.event_system import EventType, get_event_system
from src.systems.molecular_analyzer import MolecularAnalyzer

class MoleculeDetector:
    """Detecta moleculas conocidas y genera eventos."""
    
    def __init__(self):
        event_sys = get_event_system()
        self.detector = event_sys['detector']
        self.history = event_sys['history']
        self.timeline = event_sys['timeline']
        
        # History of unique molecules found in this session
        self.discovered_formulas = set()
        
        self.check_interval = 60  # Cada 60 frames (1 segundo aprox)
        self.last_check_frame = 0
        
        # Cache: Skip BFS if bond count unchanged
        self.last_bonds_count = -1  # Force first scan
        
        # Statistics for F3 panel
        self.stats = {
            'total_molecules': 0,      # All molecules found in last scan
            'known_molecules': 0,      # Molecules with known names
            'transitory_states': 0,    # Estados transitorios detectados
            'unique_discoveries': 0,   # First-time discoveries this session
            'last_scan_formulas': {},  # formula -> count from last scan
        }
        
        # Composition Cache: tuple(sorted_indices) -> formula
        self._composition_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def detect_molecules_fast(self, atom_types_np, molecule_id_np, num_enlaces_np, n_particles):
        """
        FAST VERSION: Usa molecule_id ya propagado en GPU (sin BFS en CPU).
        El GPU ya ejecutó reset_molecule_ids() + propagate_molecule_ids_step().
        Solo necesitamos agrupar por ID y calcular fórmulas.
        """
        from collections import defaultdict
        
        # 1. Agrupar partículas por molecule_id (O(N) lineal)
        molecules = defaultdict(list)
        for i in range(n_particles):
            if num_enlaces_np[i] > 0:  # Solo partículas con enlaces
                mid = molecule_id_np[i]
                if mid >= 0:  # Include ID=0 (player often has index 0)
                    molecules[mid].append(i)
        
        # 2. Procesar cada molécula
        current_scan_formulas = {}
        
        for mid, indices in molecules.items():
            if len(indices) < 2:
                continue
            
            # 2.1 Caching Check: Hashing composition
            indices.sort()
            comp_key = tuple(indices)
            
            formula = ""
            if comp_key in self._composition_cache:
                formula = self._composition_cache[comp_key]
                self._cache_hits += 1
            else:
                formula = self._build_formula(indices, atom_types_np)
                self._composition_cache[comp_key] = formula
                self._cache_misses += 1
            
            current_scan_formulas[formula] = current_scan_formulas.get(formula, 0) + 1
            
            # 2.2 Registro de descubrimientos (Solo si es nuevo en esta sesión)
            if formula not in self.discovered_formulas:
                self.discovered_formulas.add(formula)
                
                from src.config.molecules import get_molecule_name
                real_name = get_molecule_name(formula)
                
                from src.gameplay.inventory import get_inventory
                is_new_record = get_inventory().register_discovery(formula, real_name)
                
                if is_new_record and real_name != "Transitorio":
                    from src.core.context import get_context
                    get_context().add_log(f"✨ DESCUBRIMIENTO: {real_name} ({formula})")
                    print(f"✨ [DISCOVERY] Nueva Molécula detectada: {formula} ({real_name})")
                    
                    self.detector.create_event(
                        EventType.COMPLEX_STRUCTURE,
                        f"Nueva Estructura: {formula}",
                        count=1
                    )
        
        # Periocically clean cache to avoid memory leak if many transient states occur
        if len(self._composition_cache) > 2000:
             self._composition_cache.clear()
             print("[CHEM] 🧹 Cache de química limpiado.")
        
        # 3. Actualizar stats
        total_mols = sum(current_scan_formulas.values())
        known_count = 0
        from src.config.molecules import MOLECULES
        for formula in current_scan_formulas:
            if formula in MOLECULES:
                known_count += current_scan_formulas[formula]
        
        self.stats['total_molecules'] = total_mols
        self.stats['known_molecules'] = known_count
        self.stats['transitory_states'] = total_mols - known_count
        self.stats['unique_discoveries'] = len(self.discovered_formulas)
        self.stats['last_scan_formulas'] = current_scan_formulas
    
    def detect_molecules(self, atom_types_np, enlaces_idx_np, num_enlaces_np, molecule_id_np, n_particles):
        """
        LEGACY VERSION: Mantiene compatibilidad pero usa versión rápida internamente.
        """
        # Usar versión rápida
        self.detect_molecules_fast(atom_types_np, molecule_id_np, num_enlaces_np, n_particles)

    def _bfs_molecule(self, start_idx, enlaces_idx, num_enlaces):
        """Delegated to MolecularAnalyzer for consistency."""
        return MolecularAnalyzer.get_molecule_indices(start_idx, enlaces_idx, num_enlaces)

    def _build_formula(self, indices, atom_types):
        """Delegated to MolecularAnalyzer for consistency."""
        return MolecularAnalyzer.get_formula(indices, atom_types)


# Singleton global
_molecule_detector = None

def get_molecule_detector():
    global _molecule_detector
    if _molecule_detector is None:
        _molecule_detector = MoleculeDetector()
    return _molecule_detector
