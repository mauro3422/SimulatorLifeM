"""
Spatial Hashing para Detección de Colisiones O(N)
==================================================
En vez de comparar todas las partículas entre sí (O(N²)),
dividimos el espacio en una grilla y solo comparamos
partículas en celdas vecinas (O(N)).
"""
import numpy as np
from collections import defaultdict

class SpatialGrid:
    def __init__(self, cell_size, width, height):
        """
        Args:
            cell_size: Tamaño de cada celda (debe ser >= diámetro máximo de partícula)
            width, height: Dimensiones del espacio de simulación
        """
        self.cell_size = cell_size
        self.width = width
        self.height = height
        self.cols = int(np.ceil(width / cell_size))
        self.rows = int(np.ceil(height / cell_size))
        self.grid = defaultdict(list)
    
    def clear(self):
        """Limpia la grilla para el siguiente frame."""
        self.grid.clear()
    
    def _hash(self, x, y):
        """Convierte coordenadas a índice de celda."""
        col = int(x / self.cell_size)
        row = int(y / self.cell_size)
        # Clamp a los límites
        col = max(0, min(col, self.cols - 1))
        row = max(0, min(row, self.rows - 1))
        return (col, row)
    
    def insert(self, idx, x, y):
        """Inserta una partícula en la celda correspondiente."""
        cell = self._hash(x, y)
        self.grid[cell].append(idx)
    
    def insert_all(self, positions):
        """Inserta todas las partículas de una vez (vectorizado)."""
        self.clear()
        for idx, (x, y) in enumerate(positions):
            self.insert(idx, x, y)
    
    def get_neighbors(self, idx, x, y):
        """
        Devuelve los índices de partículas en celdas vecinas.
        No incluye a la partícula misma.
        """
        col, row = self._hash(x, y)
        neighbors = []
        
        # Revisar celda actual y 8 vecinas
        for dc in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                nc, nr = col + dc, row + dr
                if 0 <= nc < self.cols and 0 <= nr < self.rows:
                    for other_idx in self.grid.get((nc, nr), []):
                        if other_idx != idx:
                            neighbors.append(other_idx)
        
        return neighbors
    
    def get_potential_pairs(self, positions):
        """
        Devuelve todos los pares de partículas que podrían colisionar.
        Esto es lo que usamos para optimizar el cálculo de colisiones.
        
        Returns:
            Set de tuplas (i, j) donde i < j
        """
        pairs = set()
        
        for idx, (x, y) in enumerate(positions):
            neighbors = self.get_neighbors(idx, x, y)
            for other_idx in neighbors:
                # Evitar duplicados: solo agregar si i < j
                if idx < other_idx:
                    pairs.add((idx, other_idx))
        
        return pairs


def create_collision_mask_optimized(positions, radii, spatial_grid):
    """
    Crea la máscara de colisiones usando spatial hashing.
    Solo calcula distancias para pares potenciales.
    
    Returns:
        collision_mask: Matriz booleana [N, N] con True donde hay colisión
    """
    n = len(positions)
    collision_mask = np.zeros((n, n), dtype=bool)
    
    # Actualizar la grilla con las posiciones actuales
    spatial_grid.insert_all(positions)
    
    # Obtener pares potenciales
    pairs = spatial_grid.get_potential_pairs(positions)
    
    # Calcular colisiones solo para pares potenciales
    for i, j in pairs:
        dist = np.linalg.norm(positions[i] - positions[j])
        sum_radii = radii[i] + radii[j]
        
        if dist < sum_radii:
            collision_mask[i, j] = True
            collision_mask[j, i] = True
    
    return collision_mask


def solve_collisions_optimized(positions, velocities, radii, spatial_grid):
    """
    Resuelve colisiones usando spatial hashing para optimización.
    
    Returns:
        Nuevas posiciones y velocidades corregidas
    """
    n = len(positions)
    
    # Actualizar la grilla
    spatial_grid.insert_all(positions)
    
    # Obtener pares potenciales
    pairs = spatial_grid.get_potential_pairs(positions)
    
    # Acumular correcciones
    pos_correction = np.zeros_like(positions)
    vel_correction = np.zeros_like(velocities)
    
    for i, j in pairs:
        diff = positions[i] - positions[j]
        dist = np.linalg.norm(diff)
        sum_radii = radii[i] + radii[j]
        
        if dist < sum_radii and dist > 0:
            # Hay colisión
            overlap = sum_radii - dist
            direction = diff / dist
            
            # Corrección simétrica (50% cada uno)
            correction = direction * overlap * 0.5
            pos_correction[i] += correction
            pos_correction[j] -= correction
            
            # Damping de velocidad
            vel_correction[i] -= correction * 0.5
            vel_correction[j] += correction * 0.5
    
    return positions + pos_correction, velocities + vel_correction
