"""
Molecular Analyzer - Sistema de Análisis Molecular
===================================================
Analiza formación de moléculas, ángulos de enlace, duración y estabilidad.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import time
import math


@dataclass
class MoleculeSnapshot:
    """Estado de una molécula en un momento dado."""
    formula: str
    atom_indices: List[int]
    center: np.ndarray
    num_atoms: int
    bond_angles: List[float]  # Ángulos en grados
    birth_frame: int
    last_seen_frame: int
    is_stable: bool = True    # Si rompió algún enlace interno recientemente
    
    
@dataclass
class MoleculeStats:
    """Estadísticas de una fórmula molecular."""
    formula: str
    times_formed: int = 0
    times_destroyed: int = 0
    total_lifetime_frames: int = 0
    max_lifetime_frames: int = 0
    avg_angles: List[float] = field(default_factory=list)
    
    @property
    def avg_lifetime(self) -> float:
        if self.times_formed == 0:
            return 0.0
        return self.total_lifetime_frames / self.times_formed


class MolecularAnalyzer:
    """
    Analiza la química de la simulación en tiempo real.
    
    Trackea:
    - Formación y destrucción de moléculas
    - Duración de vida de cada tipo de molécula
    - Ángulos de enlace reales vs ideales
    - Estabilidad y patrones químicos
    """
    
    # Ángulos VSEPR ideales por número de enlaces
    IDEAL_ANGLES = {
        2: 180.0,   # Lineal
        3: 120.0,   # Trigonal plana
        4: 109.5,   # Tetraédrica
    }
    
    # Ángulos específicos por tipo de átomo (índice)
    ATOM_SPECIFIC_ANGLES = {
        (3, 2): 104.5,  # Oxígeno con 2 enlaces (agua)
        (2, 3): 107.0,  # Nitrógeno con 3 enlaces (amoníaco)
    }
    
    @staticmethod
    def get_molecule_indices(start_idx, enlaces_idx, num_enlaces):
        """Standard graph traversal to find all atoms in a connected molecule."""
        molecule = {start_idx}
        queue = [start_idx]
        while queue:
            curr = queue.pop(0)
            n_bonds = num_enlaces[curr]
            for k in range(n_bonds):
                neighbor = enlaces_idx[curr, k]
                if neighbor >= 0 and neighbor not in molecule:
                    molecule.add(neighbor)
                    queue.append(neighbor)
        return list(molecule)

    @staticmethod
    def get_formula(indices, atom_types):
        """Standard formula builder (e.g., H2O1) - Optimized V2."""
        from src.config.atoms import TIPOS_NOMBRES
        counts = {}
        for idx in indices:
            t = int(atom_types[idx])
            sym = TIPOS_NOMBRES[t]
            counts[sym] = counts.get(sym, 0) + 1
        
        # Consistent sorting: C first, H second, then alphabetical
        # Hill system ordering
        res = ""
        # 1. Carbon
        if 'C' in counts:
            res += f"C{counts.pop('C')}"
        # 2. Hydrogen
        if 'H' in counts:
            res += f"H{counts.pop('H')}"
        # 3. Everything else alphabetical
        if counts:
            for s in sorted(counts.keys()):
                res += f"{s}{counts[s]}"
        return res

    def __init__(self):
        self.current_frame = 0
        self.active_molecules: Dict[int, MoleculeSnapshot] = {}
        self.formula_stats: Dict[str, MoleculeStats] = defaultdict(
            lambda formula=None: MoleculeStats(formula=formula or "Unknown")
        )
        
        # Últimos eventos para UI
        self.recent_formations: List[str] = []
        self.recent_destructions: List[str] = []
        self.max_recent = 10
        
        # Análisis de ángulos
        self.angle_samples: Dict[str, List[float]] = defaultdict(list)
        self.max_samples = 100
        
        # Nuevas Métricas (Health & Energy)
        self.kinetic_energy_history: List[float] = []
        self.emergence_events: List[int] = [] # Frame IDs where new molecules formed
        self.z_stability_history: List[float] = [] # Avg Z-spread / Avg Bond Length ratio
        
        # Debug
        self.last_analysis_time = 0.0
        
    def reset(self):
        """Limpia todo el estado del analizador."""
        self.active_molecules = {}
        self.formula_stats = defaultdict(lambda formula=None: MoleculeStats(formula=formula or "Unknown"))
        self.recent_formations = []
        self.recent_destructions = []
        self.angle_samples = defaultdict(list)
        self.current_frame = 0
        print("[ANALYZER] 🧹 Estadísticas reseteadas.")
        
    def analyze_frame(self, pos_np: np.ndarray, pos_z_np: np.ndarray,
                      atom_types_np: np.ndarray, 
                      enlaces_idx_np: np.ndarray, num_enlaces_np: np.ndarray,
                      molecule_id_np: np.ndarray, is_active_np: np.ndarray) -> Dict:
        """
        Analiza el estado molecular del frame actual.
        
        Returns:
            Dict con estadísticas y eventos del frame.
        """
        self.current_frame += 1
        start_time = time.time()
        
        # 1. Escanear moléculas actuales
        current_molecules = self._scan_molecules(
            pos_np, pos_z_np, atom_types_np, enlaces_idx_np, 
            num_enlaces_np, molecule_id_np, is_active_np
        )
        
        # 2. Detectar formaciones y destrucciones
        formations, destructions = self._detect_changes(current_molecules)
        
        # 3. Analizar ángulos de moléculas activas
        angle_analysis = self._analyze_angles(
            current_molecules, pos_np, pos_z_np, enlaces_idx_np, num_enlaces_np
        )
        
        # 4. Actualizar estadísticas
        self._update_stats(formations, destructions)
        
        # 5. Calcular métricas de salud física (Energía y Z)
        phys_metrics = self._calculate_physics_health(pos_np, pos_z_np, current_molecules)
        
        # 6. Guardar estado actual
        self.active_molecules = current_molecules
        
        self.last_analysis_time = (time.time() - start_time) * 1000  # ms
        
        return {
            'formations': formations,
            'destructions': destructions,
            'angle_analysis': angle_analysis,
            'physics_health': phys_metrics,
            'active_count': len(current_molecules),
            'analysis_time_ms': self.last_analysis_time
        }
        
    def _scan_molecules(self, pos_np, pos_z_np, atom_types_np, enlaces_idx_np, 
                        num_enlaces_np, molecule_id_np, is_active_np) -> Dict[int, MoleculeSnapshot]:
        """Escanea todas las moléculas activas."""
        molecules = {}
        mol_groups = defaultdict(list)
        
        # Agrupar átomos por molecule_id
        for i in range(len(pos_np)):
            if is_active_np[i] and num_enlaces_np[i] > 0:
                mid = molecule_id_np[i]
                if mid >= 0:  # Changed from > 0 to include ID 0
                    mol_groups[mid].append(i)
        
        # Procesar cada grupo
        ATOM_SYMBOLS = ['C', 'H', 'N', 'O', 'P', 'S']
        
        for mid, indices in mol_groups.items():
            if len(indices) < 2:
                continue
                
            # Calcular fórmula usando el método unificado
            formula = self.get_formula(indices, atom_types_np)
            
            # Calcular centro
            positions = pos_np[indices]
            center = np.mean(positions, axis=0)
            
            # Calcular ángulos (3D REAL)
            angles = self._measure_bond_angles(indices, pos_np, pos_z_np, enlaces_idx_np, num_enlaces_np)
            
            molecules[mid] = MoleculeSnapshot(
                formula=formula,
                atom_indices=indices,
                center=center,
                num_atoms=len(indices),
                bond_angles=angles,
                birth_frame=self.active_molecules.get(mid, MoleculeSnapshot(
                    formula=formula, atom_indices=[], center=np.zeros(2),
                    num_atoms=0, bond_angles=[], birth_frame=self.current_frame,
                    last_seen_frame=self.current_frame
                )).birth_frame,
                last_seen_frame=self.current_frame
            )
            
        return molecules
        
    def _measure_bond_angles(self, indices: List[int], pos_np: np.ndarray, pos_z_np: np.ndarray,
                             enlaces_idx_np: np.ndarray, num_enlaces_np: np.ndarray) -> List[float]:
        """Mide ángulos de enlace reales en 3D (Sistema 2.5D)."""
        angles = []
        
        for i in indices:
            n_bonds = num_enlaces_np[i]
            if n_bonds >= 2:
                p_center = np.array([pos_np[i][0], pos_np[i][1], pos_z_np[i]])
                neighbors = []
                
                for b in range(n_bonds):
                    j = enlaces_idx_np[i, b]
                    if j >= 0:
                        neighbors.append(j)
                
                # Calcular ángulos entre pares de vecinos en 3D
                for a in range(len(neighbors)):
                    for b in range(a + 1, len(neighbors)):
                        j1, j2 = neighbors[a], neighbors[b]
                        v1 = np.array([pos_np[j1][0], pos_np[j1][1], pos_z_np[j1]]) - p_center
                        v2 = np.array([pos_np[j2][0], pos_np[j2][1], pos_z_np[j2]]) - p_center
                        
                        len1 = np.linalg.norm(v1)
                        len2 = np.linalg.norm(v2)
                        
                        if len1 > 0.001 and len2 > 0.001:
                            cos_angle = np.clip(np.dot(v1, v2) / (len1 * len2), -1.0, 1.0)
                            angle_deg = math.degrees(math.acos(cos_angle))
                            angles.append(angle_deg)
                            
        return angles
        
    def _detect_changes(self, current: Dict[int, MoleculeSnapshot]) -> Tuple[List[str], List[str]]:
        """Detecta moléculas formadas y destruidas."""
        formations = []
        destructions = []
        
        # Nuevas moléculas (en current pero no en active)
        for mid, mol in current.items():
            if mid not in self.active_molecules:
                formations.append(mol.formula)
                self.recent_formations.append(f"[{self.current_frame}] +{mol.formula}")
                if len(self.recent_formations) > self.max_recent:
                    self.recent_formations.pop(0)
        
        # Moléculas destruidas (en active pero no en current)
        for mid, mol in self.active_molecules.items():
            if mid not in current:
                destructions.append(mol.formula)
                lifetime = mol.last_seen_frame - mol.birth_frame
                self.recent_destructions.append(f"[{self.current_frame}] -{mol.formula} ({lifetime}f)")
                if len(self.recent_destructions) > self.max_recent:
                    self.recent_destructions.pop(0)
                    
        return formations, destructions
        
    def _analyze_angles(self, molecules: Dict[int, MoleculeSnapshot],
                        pos_np: np.ndarray, pos_z_np: np.ndarray, enlaces_idx_np: np.ndarray, 
                        num_enlaces_np: np.ndarray) -> Dict:
        """Analiza ángulos de enlace y compara con ideales."""
        all_angles = []
        angle_errors = []
        
        for mol in molecules.values():
            for angle in mol.bond_angles:
                all_angles.append(angle)
                
                # Guardar muestras por fórmula
                if len(self.angle_samples[mol.formula]) < self.max_samples:
                    self.angle_samples[mol.formula].append(angle)
        
        if not all_angles:
            return {'avg': 0, 'std': 0, 'min': 0, 'max': 0, 'count': 0}
            
        return {
            'avg': np.mean(all_angles),
            'std': np.std(all_angles),
            'min': np.min(all_angles),
            'max': np.max(all_angles),
            'count': len(all_angles)
        }
        
        
    def _calculate_physics_health(self, pos_np, pos_z_np, current_mols) -> Dict:
        """Calcula métricas de salud física (Z-Stability y Energía)."""
        # 1. Z-Stability (Ratio Z-Spread vs Bond Length)
        ratios = []
        for mol in current_mols.values():
            if len(mol.atom_indices) >= 2:
                # Estimación simple de bond length promedio (usamos centro a átomo como proxy rápido)
                avg_dist = np.mean([np.linalg.norm(pos_np[i] - mol.center) for i in mol.atom_indices])
                z_spread = np.max(pos_z_np[mol.atom_indices]) - np.min(pos_z_np[mol.atom_indices])
                if avg_dist > 0.1:
                    ratios.append(z_spread / avg_dist)
        
        z_stability = np.mean(ratios) if ratios else 0.0
        self.z_stability_history.append(z_stability)
        
        return {
            'z_stability': z_stability
        }

    def _calculate_emergence_velocity(self) -> float:
        """Retorna moléculas nuevas por cada 1000 frames (basado en los últimos 500 frames)."""
        window = 500
        recent_events = [f for f in self.emergence_events if f > self.current_frame - window]
        return (len(recent_events) / window) * 1000 if window > 0 else 0.0

    def _calculate_energy_volatility(self) -> float:
        """Mide qué tan inestable es la energía cinética (desviación estándar relativa)."""
        if len(self.kinetic_energy_history) < 10:
            return 0.0
        recent = self.kinetic_energy_history[-50:]
        return np.std(recent) / (np.mean(recent) + 1e-6)

    def _update_stats(self, formations: List[str], destructions: List[str]):
        """Actualiza estadísticas globales."""
        if formations:
            self.emergence_events.append(self.current_frame)
            
        for formula in formations:
            stats = self.formula_stats[formula]
            stats.formula = formula
            stats.times_formed += 1
            
        for formula in destructions:
            # Buscar la molécula destruida para calcular lifetime
            for mid, mol in self.active_molecules.items():
                if mol.formula == formula:
                    lifetime = mol.last_seen_frame - mol.birth_frame
                    stats = self.formula_stats[formula]
                    stats.times_destroyed += 1
                    stats.total_lifetime_frames += lifetime
                    stats.max_lifetime_frames = max(stats.max_lifetime_frames, lifetime)
                    break
                    
    def get_summary(self) -> Dict:
        """Retorna un resumen de estadísticas."""
        # Top 5 más formadas
        top_formed = sorted(
            self.formula_stats.values(),
            key=lambda s: s.times_formed,
            reverse=True
        )[:5]
        
        # Top 5 más estables (mayor lifetime)
        top_stable = sorted(
            self.formula_stats.values(),
            key=lambda s: s.avg_lifetime if s.avg_lifetime > 0 else 0,
            reverse=True
        )[:5]
        
        return {
            'active_molecules': len(self.active_molecules),
            'unique_formulas': len(self.formula_stats),
            'total_formations': sum(s.times_formed for s in self.formula_stats.values()),
            'total_destructions': sum(s.times_destroyed for s in self.formula_stats.values()),
            'top_formed': [(s.formula, s.times_formed) for s in top_formed],
            'top_stable': [(s.formula, s.avg_lifetime) for s in top_stable if s.avg_lifetime > 0],
            'recent_formations': self.recent_formations[-5:],
            'recent_destructions': self.recent_destructions[-5:],
            'emergence_velocity': self._calculate_emergence_velocity(),
            'z_stability_avg': np.mean(self.z_stability_history[-100:]) if self.z_stability_history else 1.0,
            'energy_volatility': self._calculate_energy_volatility()
        }


# Singleton global
_analyzer: Optional[MolecularAnalyzer] = None

def get_molecular_analyzer() -> MolecularAnalyzer:
    """Retorna la instancia singleton del analizador."""
    global _analyzer
    if _analyzer is None:
        _analyzer = MolecularAnalyzer()
    return _analyzer
