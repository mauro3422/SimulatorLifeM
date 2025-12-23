"""
ParticleRenderer - Renderizado OpenGL de partículas y enlaces.
Extraído de main.py para modularización.
"""

import moderngl
from src.config import UIConfig
import src.config as cfg
import numpy as np

# Shaders centralizados
from src.renderer.shader_sources import (
    PARTICLE_VERTEX, PARTICLE_FRAGMENT,
    BOND_VERTEX, BOND_FRAGMENT,
    RING_VERTEX, RING_FRAGMENT,
    RING_COLORED_VERTEX, RING_COLORED_FRAGMENT,
    BUBBLE_VERTEX, BUBBLE_FRAGMENT,
)


class ParticleRenderer:
    """Renderizador de partículas usando ModernGL con shaders GLSL."""
    
    def __init__(self, ctx, max_particles: int, max_bond_vertices: int):
        """
        Args:
            ctx: Contexto ModernGL
            max_particles: Número máximo de partículas a renderizar
            max_bond_vertices: Número máximo de vértices para enlaces
        """
        self.ctx = ctx
        self.max_particles = max_particles
        self.max_bond_vertices = max_bond_vertices
        
        # 1. Shader de Partículas (VIVID con 2.5D Depth + Desaturación)
        self.prog = ctx.program(
            vertex_shader=PARTICLE_VERTEX,
            fragment_shader=PARTICLE_FRAGMENT,
        )
        
        # 2. Shader de Enlaces
        self.bond_prog = ctx.program(
            vertex_shader=BOND_VERTEX,
            fragment_shader=BOND_FRAGMENT,
        )

        # 3. Shader de Anillos (SDF)
        self.ring_prog = ctx.program(
            vertex_shader=RING_VERTEX,
            fragment_shader=RING_FRAGMENT,
        )

        # 4. Shader para anillos COLOREADOS (Per-instance color)
        self.ring_prog_colored = ctx.program(
            vertex_shader=RING_COLORED_VERTEX,
            fragment_shader=RING_COLORED_FRAGMENT,
        )

        # 5. Shader para Burbujas LOD (Filled Circles + Per Instance Radius)
        self.bubble_prog = ctx.program(
            vertex_shader=BUBBLE_VERTEX,
            fragment_shader=BUBBLE_FRAGMENT,
        )
        
        # VBOs para partículas (with 2.5D scale)
        self.vbo_pos = ctx.buffer(reserve=max_particles * 8)
        self.vbo_col = ctx.buffer(reserve=max_particles * 12)
        self.vbo_scale = ctx.buffer(reserve=max_particles * 4)  # 1 float per particle
        self.vao = ctx.vertex_array(self.prog, [
            (self.vbo_pos, '2f', 'in_vert'),
            (self.vbo_col, '3f', 'in_color'),
            (self.vbo_scale, '1f', 'in_scale'),
        ])
        
        # VBOs LOD Bubbles
        self.vbo_bub_pos = ctx.buffer(reserve=max_particles * 8)
        self.vbo_bub_col = ctx.buffer(reserve=max_particles * 16)
        self.vbo_bub_rad = ctx.buffer(reserve=max_particles * 4)
        self.vao_bubbles = ctx.vertex_array(self.bubble_prog, [
            (self.vbo_bub_pos, '2f', 'in_vert'),
            (self.vbo_bub_col, '4f', 'in_color'),
            (self.vbo_bub_rad, '1f', 'in_radius'),
        ])
        
        # VBOs para enlaces
        self.vbo_bonds = ctx.buffer(reserve=max_bond_vertices * 8)
        self.vao_bonds = ctx.vertex_array(self.bond_prog, [
            (self.vbo_bonds, '2f', 'in_vert'),
        ])
        
        # VBO para debug (bordes)
        self.vbo_debug = ctx.buffer(reserve=16 * 8)
        self.vao_debug = ctx.vertex_array(self.bond_prog, [
            (self.vbo_debug, '2f', 'in_vert'),
        ])

        # VAO para Destacados (Picking - líneas de conexión)
        self.vbo_select = ctx.buffer(reserve=100000 * 8) 
        self.vao_select = ctx.vertex_array(self.bond_prog, [
            (self.vbo_select, '2f', 'in_vert'),
        ])
        
        # VAO para Anillos SDF (usa ring_prog, no bond_prog)
        self.vbo_rings = ctx.buffer(reserve=10000 * 8)  # 10K átomo centers
        self.vao_rings = ctx.vertex_array(self.ring_prog, [
            (self.vbo_rings, '2f', 'in_vert'),
        ])

        # VAO para Anillos COLOREADOS
        self.vbo_rings_c_pos = ctx.buffer(reserve=10000 * 8)
        self.vbo_rings_c_col = ctx.buffer(reserve=10000 * 16) # RGBA float
        self.vao_rings_colored = ctx.vertex_array(self.ring_prog_colored, [
            (self.vbo_rings_c_pos, '2f', 'in_vert'),
            (self.vbo_rings_c_col, '4f', 'in_color'),
        ])

    def render(self, pos_data, col_data, scale_data=None, bond_data=None, debug_data=None, 
               highlight_data=None, width=1280, height=720, camera_params=None, bonds_only=False,
               alpha=1.0):
        """
        Renderiza partículas, enlaces y elementos de debug.
        Args:
            scale_data: (N, 1) array with 2.5D depth scale factors
            camera_params: tuple (cx, cy, vis_w_half, vis_h_half) para transformación
        """
        if camera_params is None:
            # Fallback para evitar crashes si no se pasa
            cx, cy, vis_w_half, vis_h_half = 0, 0, 1, 1
        else:
            cx, cy, vis_w_half, vis_h_half = camera_params

        # Calcular escalas (invertimos Y en el shader explícitamente)
        scale_x = 1.0 / vis_w_half
        scale_y = 1.0 / vis_h_half
        self.ctx.viewport = (0, 0, width, height)
        # Estados GL base
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Configurar Uniforms Globales
        self.prog['u_offset'].value = (cx, cy)
        self.prog['u_scale'].value = (scale_x, scale_y)
        self.prog['u_global_alpha'].value = float(alpha)
        
        self.bond_prog['u_offset'].value = (cx, cy)
        self.bond_prog['u_scale'].value = (scale_x, scale_y)
        self.bond_prog['u_global_alpha'].value = float(alpha)

        # Renderizar enlaces
        if bond_data is not None and len(bond_data) > 0:
            self.vbo_bonds.orphan()  # Avoid GPU sync stall
            self.vbo_bonds.write(bond_data.tobytes())
            self.bond_prog['color'].value = (0.5, 1.0, 0.5, 0.4)
            # Aplicar grosor maestro desde configuración
            self.ctx.line_width = cfg.sim_config.BOND_WIDTH
            self.vao_bonds.render(moderngl.LINES, vertices=len(bond_data))
            # Segunda pasada para brillo
            self.bond_prog['color'].value = (0.6, 1.0, 0.6, 0.2)
            self.vao_bonds.render(moderngl.LINES, vertices=len(bond_data))

        # Renderizar debug (bordes de mundo y pantalla)
        if debug_data is not None:
            self.vbo_debug.orphan()  # Avoid GPU sync stall
            self.vbo_debug.write(debug_data.tobytes())
            self.bond_prog['color'].value = (0.8, 0.2, 0.2, 0.8)
            self.vao_debug.render(moderngl.LINES, vertices=8)
            self.bond_prog['color'].value = (0.4, 0.8, 1.0, 0.8)
            self.vao_debug.render(moderngl.LINES, vertices=8, first=8)

        # Renderizar partículas con efecto 2.5D
        if not bonds_only and pos_data is not None and len(pos_data) > 0:
            # Orphan buffers to avoid GPU sync stalls
            self.vbo_pos.orphan()
            self.vbo_col.orphan()
            self.vbo_pos.write(pos_data.tobytes())
            self.vbo_col.write(col_data.tobytes())
            
            # 2.5D depth scale
            if scale_data is not None and len(scale_data) > 0:
                self.vbo_scale.orphan()  # Avoid GPU sync stall
                self.vbo_scale.write(scale_data.astype('float32').tobytes())
            else:
                # Default scale = 1.0 for all particles
                import numpy as np
                default_scale = np.ones((len(pos_data), 1), dtype=np.float32)
                self.vbo_scale.write(default_scale.tobytes())
            
            # Set base point size uniform
            self.prog['u_base_size'].value = cfg.sim_config.ATOM_SIZE_GL
            self.vao.render(moderngl.POINTS, vertices=len(pos_data))

        # Renderizar selección (destacado)
        if highlight_data is not None and len(highlight_data) > 0:
            self._render_highlight(highlight_data)
    
    def _render_highlight(self, highlight_data):
        """Renderiza líneas de conexión entre átomos seleccionados."""
        # Los anillos ahora se dibujan con render_rings (SDF shader)
        # Esta función solo dibuja las líneas de enlace
        if len(highlight_data) < 4:
            return
            
        data_bytes = highlight_data.tobytes()
        self.vbo_select.orphan()  # Avoid GPU sync stall
        if len(data_bytes) <= self.vbo_select.size:
            self.vbo_select.write(data_bytes)
        else:
            self.vbo_select.write(data_bytes[:self.vbo_select.size])
        
        # Renderizar todas las líneas como LINES (pares de vértices)
        self.ctx.line_width = UIConfig.WIDTH_SECONDARY
        # Usar el color de highlight para enlaces
        highlight_color = getattr(UIConfig, 'COLOR_HIGHLIGHT_BOND', UIConfig.COLOR_CYAN_NEON)
        self.bond_prog['color'].value = highlight_color
        num_vertices = len(highlight_data) // 2
        self.vao_select.render(moderngl.LINES, vertices=num_vertices)

    def render_rings(self, centers_data, radius_world, color, camera_params, height, alpha=1.0):
        """Renderiza anillos usando SDF."""
        if len(centers_data) == 0:
            return
            
        cx, cy, vis_w_half, vis_h_half = camera_params
        
        # Ensure VBO capacity
        n = min(len(centers_data), 10000)
        
        # Actualizar VBO y Program
        self.vbo_rings.orphan()  # Avoid GPU sync stall
        self.vbo_rings.write(centers_data[:n].tobytes())
        
        scale_x = 1.0 / vis_w_half
        scale_y = 1.0 / vis_h_half
        
        self.ring_prog['u_offset'].value = (cx, cy)
        self.ring_prog['u_scale'].value = (scale_x, scale_y)
        self.ring_prog['u_radius_world'].value = radius_world
        self.ring_prog['u_px_scale_y'].value = height / 2.0
        self.ring_prog['color'].value = color
        self.ring_prog['u_global_alpha'].value = float(alpha)
        
        self.vao_rings.render(mode=moderngl.POINTS, vertices=n)

    def render_rings_colored(self, centers_data, colors_data, radius_world, camera_params, height, alpha=1.0):
        """Renderiza anillos con colores por instancia (Quimidex Highlights)."""
        if len(centers_data) == 0:
            return
            
        cx, cy, vis_w_half, vis_h_half = camera_params
        n = min(len(centers_data), 10000)
        
        # Actualizar VBOs
        self.vbo_rings_c_pos.orphan()  # Avoid GPU sync stall
        self.vbo_rings_c_col.orphan()
        self.vbo_rings_c_pos.write(centers_data[:n].tobytes())
        self.vbo_rings_c_col.write(colors_data[:n].tobytes())
        
        # Configurar programa
        scale_x = 1.0 / vis_w_half
        scale_y = 1.0 / vis_h_half
        
        self.ring_prog_colored['u_offset'].value = (cx, cy)
        self.ring_prog_colored['u_scale'].value = (scale_x, scale_y)
        self.ring_prog_colored['u_radius_world'].value = radius_world
        self.ring_prog_colored['u_px_scale_y'].value = height / 2.0
        self.ring_prog_colored['u_global_alpha'].value = float(alpha)
        
        self.vao_rings_colored.render(mode=moderngl.POINTS, vertices=n)

    def render_zones(self, zones, camera_params, width, height, alpha=0.8):
        """
        Renderiza las zonas especiales (Arcilla, Ventilas) como grandes esferas de fondo.
        """
        if not zones:
            return
            
        cx, cy, vis_w_half, vis_h_half = camera_params
        
        # Preparar datos
        centers = []
        colors = []
        radii = []
        
        for zone in zones:
            centers.append(zone.pos)
            radii.append(zone.radius)
            if zone.type.value == "Clay":
                colors.append([0.2, 0.8, 0.4, 0.25]) # Verde esmeralda para arcilla
            else:
                colors.append([1.0, 0.4, 0.1, 0.4]) # Naranja/Rojo vivo para ventilas
        
        centers = np.array(centers, dtype=np.float32)
        colors = np.array(colors, dtype=np.float32)
        radii = np.array(radii, dtype=np.float32)
        
        n = len(zones)
        self.vbo_bub_pos.orphan()  # Avoid GPU sync stall
        self.vbo_bub_col.orphan()
        self.vbo_bub_rad.orphan()
        self.vbo_bub_pos.write(centers.tobytes())
        self.vbo_bub_col.write(colors.tobytes())
        self.vbo_bub_rad.write(radii.tobytes())
        
        # Estados GL
        self.ctx.viewport = (0, 0, width, height)
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Configurar programa
        self.bubble_prog['u_offset'].value = (cx, cy)
        self.bubble_prog['u_scale'].value = (1.0 / vis_w_half, 1.0 / vis_h_half)
        self.bubble_prog['u_px_scale_y'].value = height / 2.0
        self.bubble_prog['u_global_alpha'].value = float(alpha)
        
        self.vao_bubbles.render(mode=moderngl.POINTS, vertices=n)
        
    def render_bubbles(self, bubbles_data, camera_params, height, width, alpha=1.0):
        """Renderiza Burbujas LOD (Semantic Zoom)."""
        centers = bubbles_data['centers']
        colors = bubbles_data['colors']
        radii = bubbles_data['radii']
        
        if len(centers) == 0:
            return

        cx, cy, vis_w_half, vis_h_half = camera_params
        n = min(len(centers), 10000) # Buffer limit
        
        # Write to VBOs (orphan first to avoid GPU sync)
        self.vbo_bub_pos.orphan()
        self.vbo_bub_col.orphan()
        self.vbo_bub_rad.orphan()
        self.vbo_bub_pos.write(centers[:n].tobytes())
        self.vbo_bub_col.write(colors[:n].tobytes())
        self.vbo_bub_rad.write(radii[:n].tobytes())
        
        # Configuración de Estados GL (Necesario si no se llamó a render normal)
        self.ctx.viewport = (0, 0, width, height)
        
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Shader Uniforms
        scale_x = 1.0 / vis_w_half
        scale_y = 1.0 / vis_h_half
        
        self.bubble_prog['u_offset'].value = (cx, cy)
        self.bubble_prog['u_scale'].value = (scale_x, scale_y)
        self.bubble_prog['u_px_scale_y'].value = height / 2.0
        self.bubble_prog['u_global_alpha'].value = float(alpha)
        
        # Render
        self.vao_bubbles.render(mode=moderngl.POINTS, vertices=n)
    
    def clear_screen(self, width: int, height: int):
        """Limpia la pantalla cuando no hay partículas visibles."""
        self.ctx.viewport = (0, 0, width, height)
        self.ctx.clear(0.02, 0.02, 0.05, 1.0)
