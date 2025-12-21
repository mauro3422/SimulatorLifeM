"""
Detector de Moleculas - QuimicPYTHON
=====================================
Detecta moleculas conocidas en la simulacion y genera eventos.
"""
import numpy as np
from src.core.event_system import EventType, get_event_system

class MoleculeDetector:
    """Detecta moleculas conocidas y genera eventos."""
    
    def __init__(self):
        event_sys = get_event_system()
        self.detector = event_sys['detector']
        self.history = event_sys['history']
        self.timeline = event_sys['timeline']
        
        # Contadores para evitar spam de eventos
        self.last_water_count = 0
        self.last_organic_chain_count = 0
        self.last_complex_count = 0
        self.check_interval = 60  # Cada 60 frames
        self.last_check_frame = 0
    
    def detect_molecules(self, atom_types_np, enlaces_idx_np, num_enlaces_np, n_particles):
        """
        Escanea la simulacion y detecta moleculas conocidas.
        Genera eventos cuando se detectan nuevas moleculas.
        """
        current_frame = self.timeline.frame
        
        # Solo verificar cada N frames para no afectar rendimiento
        if current_frame - self.last_check_frame < self.check_interval:
            return
        self.last_check_frame = current_frame
        
        # Tipos: H=0, O=1, C=2, N=3
        water_count = 0
        organic_chains = 0
        complex_molecules = 0
        
        visited = set()
        
        for i in range(n_particles):
            if i in visited:
                continue
            
            # Detectar H2O: Oxigeno con 2 Hidrogenos
            if atom_types_np[i] == 1:  # Oxigeno
                h_count = 0
                h_ids = []
                for k in range(num_enlaces_np[i]):
                    j = enlaces_idx_np[i, k]
                    if j >= 0 and atom_types_np[j] == 0:  # Hidrogeno
                        h_count += 1
                        h_ids.append(j)
                
                if h_count == 2:
                    water_count += 1
                    visited.add(i)
                    visited.update(h_ids)
            
            # Detectar cadenas de carbono (C-C-C+)
            if atom_types_np[i] == 2:  # Carbono
                chain_length = self._count_carbon_chain(i, atom_types_np, enlaces_idx_np, num_enlaces_np, visited)
                if chain_length >= 3:
                    organic_chains += 1
            
            # Detectar moleculas complejas (5+ atomos conectados)
            molecule_size = self._count_molecule_size(i, enlaces_idx_np, num_enlaces_np, set())
            if molecule_size >= 5:
                complex_molecules += 1
        
        # Generar eventos si hay cambios significativos
        if water_count > self.last_water_count:
            new_water = water_count - self.last_water_count
            self.detector.create_event(
                EventType.WATER_FORMED,
                f"H2O formada! Total: {water_count}",
                count=water_count, new=new_water
            )
        self.last_water_count = water_count
        
        if organic_chains > self.last_organic_chain_count:
            new_chains = organic_chains - self.last_organic_chain_count
            self.detector.create_event(
                EventType.ORGANIC_CHAIN,
                f"Cadena C-C detectada! Total: {organic_chains}",
                count=organic_chains, new=new_chains
            )
        self.last_organic_chain_count = organic_chains
        
        if complex_molecules > self.last_complex_count:
            new_complex = complex_molecules - self.last_complex_count
            self.detector.create_event(
                EventType.COMPLEX_STRUCTURE,
                f"Molecula compleja (5+ atomos)! Total: {complex_molecules}",
                count=complex_molecules, new=new_complex
            )
        self.last_complex_count = complex_molecules
    
    def _count_carbon_chain(self, start, atom_types, enlaces_idx, num_enlaces, global_visited):
        """Cuenta la longitud de una cadena de carbonos."""
        if atom_types[start] != 2:
            return 0
        
        visited = {start}
        queue = [start]
        chain_length = 1
        
        while queue:
            current = queue.pop(0)
            for k in range(num_enlaces[current]):
                j = enlaces_idx[current, k]
                if j >= 0 and j not in visited and atom_types[j] == 2:
                    visited.add(j)
                    queue.append(j)
                    chain_length += 1
        
        global_visited.update(visited)
        return chain_length
    
    def _count_molecule_size(self, start, enlaces_idx, num_enlaces, visited):
        """Cuenta el tamano total de una molecula conectada."""
        if start in visited:
            return 0
        
        visited.add(start)
        size = 1
        
        for k in range(num_enlaces[start]):
            j = enlaces_idx[start, k]
            if j >= 0 and j not in visited:
                size += self._count_molecule_size(j, enlaces_idx, num_enlaces, visited)
        
        return size

# Singleton global
_molecule_detector = None

def get_molecule_detector():
    global _molecule_detector
    if _molecule_detector is None:
        _molecule_detector = MoleculeDetector()
    return _molecule_detector
