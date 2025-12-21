"""
ParticleRenderer - Renderizado OpenGL de partículas y enlaces.
Extraído de main.py para modularización.
"""

import moderngl
from src.config import UIConfig
import src.config as cfg


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
        
        # 1. Shader de Partículas (VIVID)
        self.prog = ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                in vec3 in_color;
                out vec3 v_color;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                    // Tamaño dinámico desde configuración central
                    gl_PointSize = %s; 
                    v_color = in_color;
                }
            ''' % cfg.sim_config.ATOM_SIZE_GL,
            fragment_shader='''
                #version 330
                in vec3 v_color;
                out vec4 f_color;
                void main() {
                    float dist = length(gl_PointCoord - 0.5);
                    if (dist > 0.5) discard;
                    float alpha = smoothstep(0.5, 0.45, dist);
                    float center = smoothstep(0.2, 0.0, dist);
                    vec3 final_col = v_color * (0.8 + 0.2 * center);
                    f_color = vec4(final_col, alpha);
                }
            ''',
        )
        
        self.bond_prog = ctx.program(
            vertex_shader='''
                #version 330
                in vec2 in_vert;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330
                uniform vec4 color;
                out vec4 f_color;
                void main() {
                    f_color = color;
                }
            ''',
        )
        
        # VBOs para partículas
        self.vbo_pos = ctx.buffer(reserve=max_particles * 8)
        self.vbo_col = ctx.buffer(reserve=max_particles * 12)
        self.vao = ctx.vertex_array(self.prog, [
            (self.vbo_pos, '2f', 'in_vert'),
            (self.vbo_col, '3f', 'in_color'),
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

        # VAO para Destacados (Picking)
        # 100,000 * 8 bytes = 800KB (Suficiente para las moléculas más extremas)
        self.vbo_select = ctx.buffer(reserve=100000 * 8) 
        self.vao_select = ctx.vertex_array(self.bond_prog, [
            (self.vbo_select, '2f', 'in_vert'),
        ])

    def render(self, pos_data, col_data, bond_data=None, debug_data=None, 
               highlight_data=None, width=1280, height=720):
        """
        Renderiza partículas, enlaces y elementos de debug.
        
        Args:
            pos_data: Array numpy de posiciones (Nx2, float32)
            col_data: Array numpy de colores (Nx3, float32)
            bond_data: Array de vértices de enlaces (opcional)
            debug_data: Array de vértices para bordes de debug (opcional)
            highlight_data: Array de vértices para selección (opcional)
            width: Ancho del viewport
            height: Alto del viewport
        """
        self.ctx.viewport = (0, 0, width, height)
        # Fondo oscuro profundo
        self.ctx.clear(0.02, 0.02, 0.05, 1.0) 
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        # Renderizar enlaces
        if bond_data is not None and len(bond_data) > 0:
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
            self.vbo_debug.write(debug_data.tobytes())
            self.bond_prog['color'].value = (0.8, 0.2, 0.2, 0.8)
            self.vao_debug.render(moderngl.LINES, vertices=8)
            self.bond_prog['color'].value = (0.4, 0.8, 1.0, 0.8)
            self.vao_debug.render(moderngl.LINES, vertices=8, first=8)

        # Renderizar partículas
        if len(pos_data) > 0:
            self.vbo_pos.write(pos_data.tobytes())
            self.vbo_col.write(col_data.tobytes())
            self.vao.render(moderngl.POINTS, vertices=len(pos_data))

        # Renderizar selección (destacado)
        if highlight_data is not None and len(highlight_data) > 0:
            self._render_highlight(highlight_data)
    
    def _render_highlight(self, highlight_data):
        """Renderiza elementos de selección/destacado."""
        # Cinturón de seguridad: evitar crash si la molécula supera el buffer
        data_bytes = highlight_data.tobytes()
        if len(data_bytes) <= self.vbo_select.size:
            self.vbo_select.write(data_bytes)
        else:
            # Escribir solo lo que quepa para no crashear
            self.vbo_select.write(data_bytes[:self.vbo_select.size])
        
        # 1. Resaltar Átomo Principal (Borde Blanco/Dorado Intenso)
        self.ctx.line_width = UIConfig.WIDTH_PRIMARY
        self.bond_prog['color'].value = UIConfig.COLOR_PRIMARY
        num_segments = UIConfig.HIGHLIGHT_SEGMENTS
        self.vao_select.render(moderngl.LINE_LOOP, vertices=num_segments) 

        # 2. Resaltar Estructura (Cian/Aqua Neón)
        if len(highlight_data) > (num_segments * 2):
            self.ctx.line_width = UIConfig.WIDTH_SECONDARY
            self.bond_prog['color'].value = UIConfig.COLOR_CYAN_NEON
            remaining_verts = (len(highlight_data) // 2) - num_segments
            if remaining_verts > 0:
                self.vao_select.render(moderngl.LINES, vertices=remaining_verts, first=num_segments)
    
    def clear_screen(self, width: int, height: int):
        """Limpia la pantalla cuando no hay partículas visibles."""
        self.ctx.viewport = (0, 0, width, height)
        self.ctx.clear(0.02, 0.02, 0.05, 1.0)
