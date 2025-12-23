"""
Depth Z - Profundidad 2.5D
===========================
Kernel para inicializar la coordenada Z de visualización.
Solo afecta a átomos sin enlaces (los enlazados usan VSEPR).
"""
import taichi as ti

from src.systems.taichi_fields import (
    is_active,
    pos_z,
    num_enlaces,
    n_particles,
)


@ti.func
def compute_depth_z_i(i: ti.i32):
    """
    Computa la coordenada Z inicial solo para átomos SIN enlaces.
    
    Para átomos con enlaces (>=1), el pos_z es manejado por
    la física VSEPR a través de vel_z y la integración.
    """
    if is_active[i]:
        if num_enlaces[i] == 0 and ti.abs(pos_z[i]) < 0.001:
            pos_z[i] = 0.0


@ti.func
def compute_depth_z_func():
    """Computa profundidad Z para todas las partículas."""
    for i in range(n_particles[None]):
        compute_depth_z_i(i)


@ti.kernel
def compute_depth_z_gpu():
    """Kernel GPU para computar profundidad 2.5D."""
    compute_depth_z_func()
