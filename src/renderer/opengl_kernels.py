"""
OpenGL Kernels - Taichi GPU Kernels para Rendering
===================================================
Kernels de preparación de datos para OpenGL ModernGL:
- Líneas de enlaces
- Cajas de debug (mundo y pantalla)
"""
import taichi as ti

from src.systems.taichi_fields import (
    pos, is_active, num_enlaces, enlaces_idx,
    n_visible, visible_indices
)
from src.config.system_constants import WORLD_SIZE, MAX_PARTICLES


# ===================================================================
# CAMPOS PARA OPENGL
# ===================================================================

MAX_BOND_VERTICES = MAX_PARTICLES * 8
bond_vertices = ti.Vector.field(2, dtype=ti.f32, shape=MAX_BOND_VERTICES)
n_bond_vertices = ti.field(dtype=ti.i32, shape=())

# Campos para Debug
border_vertices = ti.Vector.field(2, dtype=ti.f32, shape=8)
screen_box_vertices = ti.Vector.field(2, dtype=ti.f32, shape=8)


# ===================================================================
# KERNELS DE DEBUG
# ===================================================================

@ti.kernel
def update_borders_gl(zoom: ti.f32, cx: ti.f32, cy: ti.f32, aspect: ti.f32):
    """Calcula vértices de cajas de debug para OpenGL."""
    # Caja de Mundo (Roja)
    W = float(WORLD_SIZE)
    pts_w = [ti.Vector([0.0, 0.0]), ti.Vector([W, 0.0]), 
             ti.Vector([W, 0.0]), ti.Vector([W, W]),
             ti.Vector([W, W]), ti.Vector([0.0, W]),
             ti.Vector([0.0, W]), ti.Vector([0.0, 0.0])]
    
    vis_h_half = W / (2.0 * zoom)
    vis_w_half = vis_h_half * aspect
    
    for i in ti.static(range(8)):
        border_vertices[i] = ti.Vector([
            (pts_w[i][0] - cx) / vis_w_half,
            -(pts_w[i][1] - cy) / vis_h_half
        ])

    # Caja de Pantalla (Cyan) - Representa el área EXACTA de visión
    pts_s = [ti.Vector([cx - vis_w_half, cy - vis_h_half]), ti.Vector([cx + vis_w_half, cy - vis_h_half]),
             ti.Vector([cx + vis_w_half, cy - vis_h_half]), ti.Vector([cx + vis_w_half, cy + vis_h_half]),
             ti.Vector([cx + vis_w_half, cy + vis_h_half]), ti.Vector([cx - vis_w_half, cy + vis_h_half]),
             ti.Vector([cx - vis_w_half, cy + vis_h_half]), ti.Vector([cx - vis_w_half, cy - vis_h_half])]

    for i in ti.static(range(8)):
        screen_box_vertices[i] = ti.Vector([
            (pts_s[i][0] - cx) / vis_w_half,
            -(pts_s[i][1] - cy) / vis_h_half
        ])


# ===================================================================
# KERNELS DE ENLACES
# ===================================================================

@ti.kernel
def prepare_bond_lines_gl(zoom: ti.f32, cx: ti.f32, cy: ti.f32, aspect: ti.f32):
    """Prepara líneas de enlaces para OpenGL (Coordenadas -1..1)."""
    n_bond_vertices[None] = 0
    n_vis = n_visible[None]
    vis_h_half = WORLD_SIZE / (2.0 * zoom)
    vis_w_half = vis_h_half * aspect
    
    for vi in range(n_vis):
        i = visible_indices[vi]
        if is_active[i]:
            p_i = pos[i]
            v1 = ti.Vector([
                (p_i.x - cx) / vis_w_half,
                -(p_i.y - cy) / vis_h_half
            ])

            for k in range(num_enlaces[i]):
                j = enlaces_idx[i, k]
                if j > i: 
                    p_j = pos[j]
                    v2 = ti.Vector([
                        (p_j.x - cx) / vis_w_half,
                        -(p_j.y - cy) / vis_h_half
                    ])
                    
                    idx = ti.atomic_add(n_bond_vertices[None], 2)
                    if idx + 1 < MAX_BOND_VERTICES:
                        bond_vertices[idx] = v1
                        bond_vertices[idx+1] = v2
