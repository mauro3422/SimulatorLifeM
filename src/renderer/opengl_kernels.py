"""
OpenGL Kernels - Taichi GPU Kernels para Rendering (Total Unification V3)
===================================================================
Kernels de preparación de datos para OpenGL ModernGL en un solo Buffer.
"""
import taichi as ti
import numpy as np

from src.systems.taichi_fields import (
    pos, pos_z, is_active, num_enlaces, enlaces_idx, atom_types,
    n_visible, visible_indices, colors,
    n_simulated_physics, radii,
    total_bonds_count, total_mutations, total_tunnels,
    sim_bounds, active_particles_count, molecule_id
)
from src.config.system_constants import WORLD_SIZE, MAX_PARTICLES, MAX_BONDS

# Constantes de profundidad 2.5D
from src.systems import physics_constants as phys
DEPTH_Z_AMPLITUDE = phys.DEPTH_Z_AMPLITUDE
DEPTH_SIZE_FACTOR = phys.DEPTH_SIZE_FACTOR

# ===================================================================
# CAMPOS PARA OPENGL
# ===================================================================

MAX_BOND_VERTICES = MAX_PARTICLES * 8
MAX_HIGHLIGHTS = 1024

# ===================================================================
# UNIVERSAL GPU BUFFER (Total Unification V3)
# ===================================================================
# Layout (Offsets):
OFFSET_STATS      = 0      # Rows 0-1
OFFSET_PARTICLES  = 2      # Rows 2 to MAX_PARTICLES + 1
OFFSET_BONDS      = MAX_PARTICLES + 2 
OFFSET_HIGHLIGHTS = MAX_PARTICLES + MAX_BOND_VERTICES + 2
OFFSET_DEBUG      = MAX_PARTICLES + MAX_BOND_VERTICES + MAX_HIGHLIGHTS + 2

TOTAL_BUFFER_ROWS = OFFSET_DEBUG + 100
# Aumentado a 12 columnas para meter TODO el estado sincronizado
universal_gpu_buffer = ti.field(dtype=ti.f32, shape=(TOTAL_BUFFER_ROWS, 12))

render_vis_count = ti.field(dtype=ti.i32, shape=()) 
n_highlights = ti.field(dtype=ti.i32, shape=())
n_bond_vertices = ti.field(dtype=ti.i32, shape=())

# Colores de Highlight
COLOR_SEL = ti.Vector([1.0, 1.0, 1.0, 1.0]) 
COLOR_NEI = ti.Vector([0.0, 1.0, 1.0, 1.0]) 

# Compatibilidad (Obsoleto después de V3 Full)
border_vertices = ti.Vector.field(2, dtype=ti.f32, shape=8)
screen_box_vertices = ti.Vector.field(2, dtype=ti.f32, shape=8)
highlight_pos = ti.Vector.field(2, dtype=ti.f32, shape=MAX_HIGHLIGHTS)
highlight_col = ti.Vector.field(4, dtype=ti.f32, shape=MAX_HIGHLIGHTS)
bond_vertices = ti.Vector.field(2, dtype=ti.f32, shape=MAX_BOND_VERTICES)

# ===================================================================
# KERNELS DE RENDERIZADO
# ===================================================================

@ti.kernel
def update_borders_gl(zoom: ti.f32, cx: ti.f32, cy: ti.f32, aspect: ti.f32):
    """Calcula vértices de cajas de debug directamente en el Master Buffer."""
    W = float(WORLD_SIZE)
    pts_w = [ti.Vector([0.0, 0.0]), ti.Vector([W, 0.0]), 
             ti.Vector([W, 0.0]), ti.Vector([W, W]),
             ti.Vector([W, W]), ti.Vector([0.0, W]),
             ti.Vector([0.0, W]), ti.Vector([0.0, 0.0])]
    
    # CRITICAL: Update global simulation bounds for chemistry culling
    sim_bounds[0] = 0.0
    sim_bounds[1] = 0.0
    sim_bounds[2] = W
    sim_bounds[3] = W
    
    vis_h_half = W / (2.0 * zoom)
    vis_w_half = vis_h_half * aspect
    
    # World Borders
    for i in ti.static(range(4)):
        p1 = pts_w[i*2]
        p2 = pts_w[i*2+1]
        row = OFFSET_DEBUG + i
        universal_gpu_buffer[row, 0] = p1.x
        universal_gpu_buffer[row, 1] = p1.y
        universal_gpu_buffer[row + 4, 0] = p2.x
        universal_gpu_buffer[row + 4, 1] = p2.y
        # Legacy
        border_vertices[i] = p1
        border_vertices[i+4] = p2

    # Screen Box
    pts_s = [ti.Vector([cx - vis_w_half, cy - vis_h_half]), ti.Vector([cx + vis_w_half, cy - vis_h_half]),
             ti.Vector([cx + vis_w_half, cy - vis_h_half]), ti.Vector([cx + vis_w_half, cy + vis_h_half]),
             ti.Vector([cx + vis_w_half, cy + vis_h_half]), ti.Vector([cx - vis_w_half, cy + vis_h_half]),
             ti.Vector([cx - vis_w_half, cy + vis_h_half]), ti.Vector([cx - vis_w_half, cy - vis_h_half])]

    for i in ti.static(range(4)):
        p1 = pts_s[i*2]
        p2 = pts_s[i*2+1]
        row = OFFSET_DEBUG + 8 + i
        universal_gpu_buffer[row, 0] = p1.x
        universal_gpu_buffer[row, 1] = p1.y
        universal_gpu_buffer[row + 4, 0] = p2.x
        universal_gpu_buffer[row + 4, 1] = p2.y
        # Legacy
        screen_box_vertices[i] = p1
        screen_box_vertices[i+4] = p2

@ti.kernel
def compact_render_data(output_stats: ti.types.ndarray(), output_particles: ti.types.ndarray()):
    """Batcher V4: Empaqueta partículas y estadísticas en NDArrays (Slice Sync)."""
    render_vis_count[None] = 0
    count = n_visible[None]
    
    for k in range(count):
        i = visible_indices[k]
        if is_active[i]:
            idx = ti.atomic_add(render_vis_count[None], 1)
            if idx < MAX_PARTICLES:
                # 1. Fill Universal Buffer (for ModernGL VBO direct if possible, or fallback)
                row = OFFSET_PARTICLES + idx 
                p_x, p_y = pos[i].x, pos[i].y
                
                # 2.5D Depth Scale: Z normalizado * factor + 1.0
                z_norm = pos_z[i] / DEPTH_Z_AMPLITUDE  # -1.0 to 1.0
                depth_scale = 1.0 + z_norm * DEPTH_SIZE_FACTOR
                
                universal_gpu_buffer[row, 0] = p_x
                universal_gpu_buffer[row, 1] = p_y
                universal_gpu_buffer[row, 2] = colors[i].x
                universal_gpu_buffer[row, 3] = colors[i].y
                universal_gpu_buffer[row, 4] = colors[i].z
                universal_gpu_buffer[row, 5] = depth_scale
                universal_gpu_buffer[row, 6] = float(atom_types[i])
                universal_gpu_buffer[row, 7] = float(molecule_id[i])
                universal_gpu_buffer[row, 8] = float(num_enlaces[i])
                universal_gpu_buffer[row, 9] = pos_z[i]
                universal_gpu_buffer[row, 10] = float(i)

                # 2. Fill Output NDArray for FAST HOST SYNC
                output_particles[idx, 0] = p_x
                output_particles[idx, 1] = p_y
                output_particles[idx, 2] = colors[i].x
                output_particles[idx, 3] = colors[i].y
                output_particles[idx, 4] = colors[i].z
                output_particles[idx, 5] = depth_scale
                output_particles[idx, 6] = float(atom_types[i])
                output_particles[idx, 7] = float(molecule_id[i])
                output_particles[idx, 8] = float(num_enlaces[i])
                output_particles[idx, 9] = pos_z[i]
                output_particles[idx, 10] = float(i)

    # Master Stats (To NDArray)
    n_vis = float(render_vis_count[None])
    n_b_v = float(n_bond_vertices[None])
    
    output_stats[0] = n_vis
    output_stats[1] = n_b_v
    output_stats[2] = float(n_highlights[None])
    output_stats[3] = float(n_simulated_physics[None])
    output_stats[4] = float(total_bonds_count[None])
    output_stats[5] = float(total_mutations[None])
    output_stats[6] = float(total_tunnels[None])
    output_stats[7] = float(active_particles_count[None])
    
    # Mirror to universal buffer for legacy renderers
    universal_gpu_buffer[OFFSET_STATS, 0] = n_vis
    universal_gpu_buffer[OFFSET_STATS, 1] = n_b_v
    universal_gpu_buffer[OFFSET_STATS, 2] = float(n_highlights[None])
    universal_gpu_buffer[OFFSET_STATS, 3] = float(n_simulated_physics[None])
    universal_gpu_buffer[OFFSET_STATS + 1, 1] = float(active_particles_count[None])

@ti.kernel
def prepare_bond_lines_gl(zoom: ti.f32, cx: ti.f32, cy: ti.f32, aspect: ti.f32, output_bonds: ti.types.ndarray()):
    """Batcher V4: Escribe enlaces en el Master Buffer y NDArray."""
    n_bond_vertices[None] = 0
    n_vis = n_visible[None]
    
    for vi in range(n_vis):
        i = visible_indices[vi]
        if is_active[i]:
            p_i = pos[i]
            for k in range(num_enlaces[i]):
                j = enlaces_idx[i, k]
                if j > i: 
                    p_j = pos[j]
                    idx = ti.atomic_add(n_bond_vertices[None], 2)
                    if idx + 1 < MAX_BOND_VERTICES:
                        # 1. Universal Buffer (for direct GL)
                        row = OFFSET_BONDS + idx
                        universal_gpu_buffer[row, 0] = p_i.x
                        universal_gpu_buffer[row, 1] = p_i.y
                        universal_gpu_buffer[row + 1, 0] = p_j.x
                        universal_gpu_buffer[row + 1, 1] = p_j.y
                        
                        # 2. NDArray (for Fast Host Sync)
                        output_bonds[idx, 0] = p_i.x
                        output_bonds[idx, 1] = p_i.y
                        output_bonds[idx + 1, 0] = p_j.x
                        output_bonds[idx + 1, 1] = p_j.y

@ti.kernel
def prepare_highlights(selected_idx: ti.i32, show_molecule: ti.i32, output_highlights: ti.types.ndarray()):
    """Batcher V4: Escribe anillos de selección en NDArray y Master Buffer."""
    n_highlights[None] = 0
    if selected_idx >= 0 and is_active[selected_idx]:
        # Atom Ring
        p_sel = pos[selected_idx]
        idx = ti.atomic_add(n_highlights[None], 1)
        if idx < MAX_HIGHLIGHTS:
            row = OFFSET_HIGHLIGHTS + idx
            universal_gpu_buffer[row, 0] = p_sel.x
            universal_gpu_buffer[row, 1] = p_sel.y
            universal_gpu_buffer[row, 2] = COLOR_SEL.x
            universal_gpu_buffer[row, 3] = COLOR_SEL.y
            universal_gpu_buffer[row, 4] = COLOR_SEL.z
            universal_gpu_buffer[row, 5] = COLOR_SEL.w
            
            # NDArray output
            output_highlights[idx, 0] = p_sel.x
            output_highlights[idx, 1] = p_sel.y
            output_highlights[idx, 2] = COLOR_SEL.x
            output_highlights[idx, 3] = COLOR_SEL.y
            output_highlights[idx, 4] = COLOR_SEL.z
            output_highlights[idx, 5] = COLOR_SEL.w
        
        # Neighbors
        if show_molecule == 0:
            for k in range(num_enlaces[selected_idx]):
                nei = enlaces_idx[selected_idx, k]
                if nei >= 0:
                    idx_n = ti.atomic_add(n_highlights[None], 1)
                    if idx_n < MAX_HIGHLIGHTS:
                        row = OFFSET_HIGHLIGHTS + idx_n
                        universal_gpu_buffer[row, 0] = pos[nei].x
                        universal_gpu_buffer[row, 1] = pos[nei].y
                        universal_gpu_buffer[row, 2] = COLOR_NEI.x
                        universal_gpu_buffer[row, 3] = COLOR_NEI.y
                        universal_gpu_buffer[row, 4] = COLOR_NEI.z
                        universal_gpu_buffer[row, 5] = COLOR_NEI.w
                        
                        # NDArray output
                        output_highlights[idx_n, 0] = pos[nei].x
                        output_highlights[idx_n, 1] = pos[nei].y
                        output_highlights[idx_n, 2] = COLOR_NEI.x
                        output_highlights[idx_n, 3] = COLOR_NEI.y
                        output_highlights[idx_n, 4] = COLOR_NEI.z
                        output_highlights[idx_n, 5] = COLOR_NEI.w

@ti.kernel
def gather_stats():
    """Compatibilidad: No hace nada en V3."""
    pass
