import taichi as ti
import numpy as np
import moderngl
from imgui_bundle import imgui, immapp, hello_imgui
import time
import math
import os

# 1. Inicializar Taichi (Delegamos a simulation_gpu para evitar conflictos)
# ti.init(arch=ti.gpu) # Eliminado para dejar que simulation_gpu decida vulkan/opengl

from src.config import SimulationConfig
from src.ui_config import UIConfig, UIWidgets
from src.systems.simulation_gpu import (
    MAX_PARTICLES, pos, vel, radii, is_active, atom_types, 
    pos_normalized, colors, n_particles, gravity, friction, 
    temperature, max_speed, world_width, world_height,
    dist_equilibrio, spring_k, damping, rango_enlace_min, 
    rango_enlace_max, dist_rotura, max_fuerza, simulation_step_gpu,
    sim_bounds, num_enlaces, enlaces_idx, n_visible, visible_indices,
    update_grid, run_simulation_fast, manos_libres,
    prob_enlace_base, click_force, click_radius, apply_force_pulse,
    total_mutations, total_tunnels, total_bonds_count
)
import src.config as cfg
from src.core.context import get_context
from src.renderer.camera import Camera

# Constantes de mundo (Ahora desde sim_config)
WORLD_SIZE = cfg.sim_config.WORLD_SIZE
MAX_BOND_VERTICES = MAX_PARTICLES * 8
bond_vertices = ti.Vector.field(2, dtype=ti.f32, shape=MAX_BOND_VERTICES)
n_bond_vertices = ti.field(dtype=ti.i32, shape=())

# Campos para Debug
border_vertices = ti.Vector.field(2, dtype=ti.f32, shape=8)
screen_box_vertices = ti.Vector.field(2, dtype=ti.f32, shape=8)

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

class ParticleRenderer:
    def __init__(self, ctx):
        self.ctx = ctx
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
        
        self.vbo_pos = ctx.buffer(reserve=MAX_PARTICLES * 8)
        self.vbo_col = ctx.buffer(reserve=MAX_PARTICLES * 12)
        self.vao = ctx.vertex_array(self.prog, [
            (self.vbo_pos, '2f', 'in_vert'),
            (self.vbo_col, '3f', 'in_color'),
        ])
        
        self.vbo_bonds = ctx.buffer(reserve=MAX_BOND_VERTICES * 8)
        self.vao_bonds = ctx.vertex_array(self.bond_prog, [
            (self.vbo_bonds, '2f', 'in_vert'),
        ])
        
        self.vbo_debug = ctx.buffer(reserve=16 * 8)
        self.vao_debug = ctx.vertex_array(self.bond_prog, [
            (self.vbo_debug, '2f', 'in_vert'),
        ])

        # VAO para Destacados (Picking)
        # 5000 * 8 bytes = 40KB (Suficiente para moléculas muy grandes)
        self.vbo_select = ctx.buffer(reserve=5000 * 8) 
        self.vao_select = ctx.vertex_array(self.bond_prog, [
            (self.vbo_select, '2f', 'in_vert'),
        ])

    def render(self, pos_data, col_data, bond_data=None, debug_data=None, highlight_data=None, width=1280, height=720):
        self.ctx.viewport = (0, 0, width, height)
        # Fondo oscuro profundo
        self.ctx.clear(0.02, 0.02, 0.05, 1.0) 
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        
        if bond_data is not None and len(bond_data) > 0:
            self.vbo_bonds.write(bond_data.tobytes())
            self.bond_prog['color'].value = (0.5, 1.0, 0.5, 0.4)
            # Aplicar grosor maestro desde configuración
            self.ctx.line_width = cfg.sim_config.BOND_WIDTH
            self.vao_bonds.render(moderngl.LINES, vertices=len(bond_data))
            # Opcional: dibujar una segunda pasada levemente más opaca si se desea más brillo
            self.bond_prog['color'].value = (0.6, 1.0, 0.6, 0.2)
            self.vao_bonds.render(moderngl.LINES, vertices=len(bond_data))

        if debug_data is not None:
            self.vbo_debug.write(debug_data.tobytes())
            self.bond_prog['color'].value = (0.8, 0.2, 0.2, 0.8)
            self.vao_debug.render(moderngl.LINES, vertices=8)
            self.bond_prog['color'].value = (0.4, 0.8, 1.0, 0.8)
            self.vao_debug.render(moderngl.LINES, vertices=8, first=8)

        if len(pos_data) > 0:
            self.vbo_pos.write(pos_data.tobytes())
            self.vbo_col.write(col_data.tobytes())
            self.vao.render(moderngl.POINTS, vertices=len(pos_data))

        # --- DIBUJAR SELECCIÓN (Destacado) ---
        if highlight_data is not None and len(highlight_data) > 0:
            self.vbo_select.write(highlight_data.tobytes())
            
            # 1. Resaltar Átomos (Círculos segmentados)
            # Cada círculo tiene 12 segmentos (24 vértices para LINES)
            # El primer grupo es el átomo principal
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

class AppState:
    def __init__(self):
        self.ctx_global = get_context()
        self.camera = self.ctx_global.init_camera(WORLD_SIZE, 1280, 720)
        self.camera.set_zoom(cfg.sim_config.INITIAL_ZOOM)
        self.paused = False
        self.time_scale = cfg.sim_config.TIME_SCALE # Sincronizado con config
        self.show_debug = False # Por defecto oculto (se activa con F3)
        self.n_particles_val = 5000 
        self.renderer = None
        self.last_time = time.time()
        self.fps = 0.0
        self.event_log = [] # Registro de eventos químicos
        self.selected_idx = -1 # Átomo seleccionado
        self.selected_mol = [] # Lista de átomos en la molécula actual
        
        # --- NUEVO: Gestión de Tiempo y Boost ---
        self.boost_active = False
        self.stored_speed = 1.0 
        self.pause_timer = 0.0
        self.last_tab_time = 0.0 # Para detección de doble tap
        
        # Métricas Acumulativas
        self.stats = {
            "bonds_formed": 0,
            "bonds_broken": 0,
            "mutations": 0,
            "tunnels": 0
        }
        
        self.init_world()
        
    def get_molecule_indices(self, start_idx):
        """Traversa los enlaces para encontrar toda la molécula conectada."""
        if start_idx < 0: return []
        
        mol = {start_idx}
        stack = [start_idx]
        
        # Obtenemos los enlaces una vez del buffer Taichi
        all_enlaces = enlaces_idx.to_numpy()
        num_v_enlaces = num_enlaces.to_numpy()
        
        while stack:
            curr = stack.pop()
            # MAX_VALENCE is 8
            for i in range(num_v_enlaces[curr]):
                neighbor = all_enlaces[curr, i]
                if neighbor >= 0 and neighbor not in mol:
                    mol.add(neighbor)
                    stack.append(neighbor)
        return list(mol)

    def get_formula(self, indices):
        """Genera una fórmula simplificada (ej: H2 O)."""
        if not indices: return ""
        counts = {}
        # Sincronización leve para leer tipos
        a_types = atom_types.to_numpy()
        for i in indices:
            t = a_types[i]
            sym = cfg.TIPOS_NOMBRES[t]
            counts[sym] = counts.get(sym, 0) + 1
        
        formula = ""
        # Orden preferido: C, H, O, N, P, S
        for s in ["C", "H", "O", "N", "P", "S"]:
            if s in counts:
                formula += f"{s}{counts[s] if counts[s] > 1 else ''} "
        for s, c in counts.items():
            if s not in ["C", "H", "O", "N", "P", "S"]:
                formula += f"{s}{c if c > 1 else ''} "
        return formula.strip()

    def add_log(self, text):
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.insert(0, f"[{timestamp}] {text}")
        if len(self.event_log) > 15:
            self.event_log.pop()
        
    def init_world(self):
        n_particles[None] = self.n_particles_val
        # Sincronizar parámetros globales desde Config Central
        gravity[None] = cfg.sim_config.GRAVITY
        friction[None] = cfg.sim_config.FRICTION
        temperature[None] = cfg.sim_config.TEMPERATURE
        max_speed[None] = cfg.sim_config.MAX_VELOCIDAD
        world_width[None] = float(WORLD_SIZE)
        world_height[None] = float(WORLD_SIZE)
        
        # Parámetros de enlaces (Centralizados)
        dist_equilibrio[None] = cfg.sim_config.DIST_EQUILIBRIO
        spring_k[None] = cfg.sim_config.SPRING_K
        damping[None] = cfg.sim_config.DAMPING
        rango_enlace_min[None] = cfg.sim_config.RANGO_ENLACE_MIN
        rango_enlace_max[None] = cfg.sim_config.RANGO_ENLACE_MAX
        dist_rotura[None] = cfg.sim_config.DIST_ROTURA
        max_fuerza[None] = cfg.sim_config.MAX_FUERZA
        
        # Parámetros de Interacción y Realismo
        prob_enlace_base[None] = cfg.sim_config.PROB_ENLACE_BASE
        click_force[None] = cfg.sim_config.CLICK_FORCE
        click_radius[None] = cfg.sim_config.CLICK_RADIUS

        # Spawning balanceado para CHONPS
        # H (40%), O (20%), C (20%), N (10%), P (5%), S (5%)
        tipos = np.random.choice([0, 1, 2, 3, 4, 5], 
                                 size=self.n_particles_val, 
                                 p=[0.4, 0.2, 0.2, 0.1, 0.05, 0.05])
        atom_types_full = np.pad(tipos, (0, MAX_PARTICLES - self.n_particles_val), constant_values=0).astype(np.int32)
        atom_types.from_numpy(atom_types_full)
        colors_table = (cfg.COLORES / 255.0).astype(np.float32)
        col_np = colors_table[atom_types_full]
        colors.from_numpy(col_np)
        radii_np = np.zeros(MAX_PARTICLES, dtype=np.float32)
        # Sincronización perfecta: Radios físicos = Radios visuales escalados
        # (Ajuste fino para que las conexiones se vean "en los núcleos")
        radii_np[:self.n_particles_val] = (cfg.RADIOS[tipos] * 1.5 + 5.0) * cfg.sim_config.SCALE
        radii.from_numpy(radii_np)
        manos_np = np.zeros(MAX_PARTICLES, dtype=np.float32)
        manos_np[:self.n_particles_val] = cfg.VALENCIAS[tipos]
        manos_libres.from_numpy(manos_np)
        margin = 1000
        pos_np = np.zeros((MAX_PARTICLES, 2), dtype=np.float32)
        pos_np[:self.n_particles_val, 0] = np.random.uniform(margin, WORLD_SIZE - margin, self.n_particles_val)
        pos_np[:self.n_particles_val, 1] = np.random.uniform(margin, WORLD_SIZE - margin, self.n_particles_val)
        pos.from_numpy(pos_np)
        is_active.from_numpy(np.pad(np.ones(self.n_particles_val, dtype=np.int32), (0, MAX_PARTICLES - self.n_particles_val), constant_values=0))
        print(f"[RESTORATION] Mundo {WORLD_SIZE}x{WORLD_SIZE} con {self.n_particles_val} partículas.")

state = AppState()

def gui():
    UIConfig.apply_style()
    io = imgui.get_io()
    display_size = io.display_size
    win_w, win_h = display_size.x, display_size.y

    # --- CONFIGURACIÓN DE LAYOUT DINÁMICO ---
    panel_left_w = UIConfig.PANEL_LEFT_W
    panel_left_h = min(680, win_h * 0.85)
    
    panel_stats_w = UIConfig.PANEL_STATS_W
    panel_stats_h = UIConfig.PANEL_STATS_H

    # --- PANEL DE CONTROL (IZQUIERDA - Glassmorphism avanzado) ---
    imgui.set_next_window_pos((20, 20), imgui.Cond_.always)
    imgui.set_next_window_size((panel_left_w, panel_left_h), imgui.Cond_.always)
    imgui.set_next_window_bg_alpha(0.75) 
    
    imgui.begin("CENTRO DE CONTROL", None, imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_resize | imgui.WindowFlags_.always_vertical_scrollbar)
    
    imgui.push_style_color(imgui.Col_.text, (0.4, 1.0, 0.8, 1.0))
    imgui.text("SISTEMA DE GESTIÓN EVOLUTIVA (CHONPS)")
    imgui.pop_style_color()
    imgui.separator()
    
    # 1. Controles de Tiempo
    # --- MONITOR DINÁMICO DE TIEMPO (TABS) ---
    UIWidgets.speed_selector(state)
    
    imgui.spacing()
    imgui.separator()
    imgui.spacing()

    # --- AJUSTES FÍSICOS (Compacto) ---
    if imgui.collapsing_header("PROPIEDADES FÍSICAS", imgui.TreeNodeFlags_.default_open):
        imgui.push_item_width(panel_left_w * 0.6)
        
        changed_g, new_g = imgui.slider_float("Gravedad", gravity[None], -10.0, 10.0, "%.3f")
        if changed_g: gravity[None] = new_g
        
        changed_f, new_f = imgui.slider_float("Fricción", friction[None], 0.8, 1.0, "%.3f")
        if changed_f: friction[None] = new_f
        
        changed_t, new_t = imgui.slider_float("Agitación", temperature[None], 0.0, 1.0, "%.3f")
        if changed_t: temperature[None] = new_t
        
        imgui.pop_item_width()

    imgui.spacing()
    imgui.separator()
    imgui.spacing()
    
    # --- GESTIÓN DE MUNDO ---
    UIWidgets.section_header("Mundo", "🌍")
    
    changed_real, val_real = imgui.checkbox("Modo Realismo (Científico)", cfg.sim_config.REALISM_MODE)
    if changed_real:
        cfg.sim_config.toggle_realism()
        # Sincronizar cambios inmediatos a la GPU
        prob_enlace_base[None] = cfg.sim_config.PROB_ENLACE_BASE
        rango_enlace_max[None] = cfg.sim_config.RANGO_ENLACE_MAX
        dist_rotura[None] = cfg.sim_config.DIST_ROTURA
        print(f"[UI] Modo Realismo: {'ON' if cfg.sim_config.REALISM_MODE else 'OFF'}")

    imgui.spacing()
    
    if imgui.button("RESTABLECER CÁMARA", (panel_left_w - 30, 35)):
        state.camera.center()
    
    if imgui.button("REINICIAR ÁTOMOS", (panel_left_w - 30, 35)):
        state.init_world()

    imgui.end()

    # --- MONITOR DE RENDIMIENTO (DERECHA - SOLO SI F3 ESTÁ ACTIVO) ---
    if state.show_debug:
        imgui.set_next_window_pos((win_w - panel_stats_w - 20, 20), imgui.Cond_.always)
        imgui.set_next_window_size((panel_stats_w, panel_stats_h), imgui.Cond_.always)
        imgui.set_next_window_bg_alpha(0.6)
        
        imgui.begin("TELEMETRÍA (F3)", None, imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_resize)
        imgui.text_colored((0.2, 0.8, 1.0, 1.0), "MONITOR DE SISTEMA")
        imgui.separator()
        imgui.text(f"FPS: {state.fps:.1f}")
        imgui.text(f"Átomos: {state.n_particles_val}")
        imgui.text_colored((1.0, 1.0, 0.4, 1.0), f"VisibleNodes: {n_visible[None]}")
        imgui.text_disabled(f"Culling: Hardware-Accelerated")
        imgui.end()

    # --- MONITOR CIENTÍFICO (DERECHA) ---
    log_h = UIConfig.LOG_H
    imgui.set_next_window_pos((win_w - panel_stats_w - 20, 20 if not state.show_debug else panel_stats_h + 40), imgui.Cond_.always)
    imgui.set_next_window_size((panel_stats_w, log_h), imgui.Cond_.always) 
    imgui.begin("MONITOR DE ACTIVIDAD MOLECULAR", None, UIConfig.WINDOW_FLAGS_LOG)
    
    UIWidgets.section_header("MÉTRICAS DE EVOLUCIÓN", "📊")
    
    imgui.begin_table("StatsInfo", 2)
    UIWidgets.metric_row("Enlaces Formados:", state.stats['bonds_formed'], UIConfig.COLOR_BOND_FORMED)
    UIWidgets.metric_row("Enlaces Rotos:", state.stats['bonds_broken'], UIConfig.COLOR_BOND_BROKEN)
    UIWidgets.metric_row("Transiciones Energ.:", state.stats['tunnels'], (0.8, 0.6, 1.0, 1.0))
    imgui.end_table()
    
    UIWidgets.section_header("BITÁCORA DE EVENTOS", "📝")
    UIWidgets.scrollable_log(state.event_log)
    
    imgui.end()

    # --- INSPECTOR MOLECULAR (INFERIOR IZQUIERDA) ---
    if state.selected_idx >= 0:
        inspect_w = UIConfig.PANEL_INSPECT_W
        inspect_h = UIConfig.PANEL_INSPECT_H
        imgui.set_next_window_pos((20, win_h - inspect_h - 20), imgui.Cond_.always)
        imgui.set_next_window_size((inspect_w, inspect_h), imgui.Cond_.always)
        imgui.set_next_window_bg_alpha(0.9)
        
        imgui.begin("INSPECTOR", None, UIConfig.WINDOW_FLAGS_STATIC)
        
        # Obtener datos del átomo seleccionado
        a_type = atom_types[state.selected_idx]
        name = cfg.TIPOS_NOMBRES[a_type]
        info = cfg.ATOMS[name]
        col = np.array(info['color']) / 255.0
        
        imgui.text_colored((col[0], col[1], col[2], 1.0), f"ÁTOMO: {name} (#{state.selected_idx})")
        imgui.separator()
        
        if not state.selected_mol:
            imgui.text(f"Masa: {info['mass']} u")
            imgui.text(f"Valencia: {info['valence']}")
            imgui.text(f"Electroneg: {info['electronegativity']}")
            imgui.spacing()
            imgui.text_wrapped(f"Info: {info['description']}")
            imgui.spacing()
            imgui.text_colored((0.2, 0.8, 1.0, 1.0), "ENLACES ADYACENTES")
            imgui.separator()
            imgui.spacing()
            imgui.text_colored((0.4, 1.0, 0.4, 1.0), "Clic de nuevo -> Expandir Molécula")
        else:
            formula = state.get_formula(state.selected_mol)
            imgui.text_colored(UIConfig.COLOR_CYAN_NEON, "SISTEMA MOLECULAR DINÁMICO")
            imgui.separator()
            imgui.text("Fórmula Química:")
            imgui.text_colored((1.0, 1.0, 1.0, 1.0), f"  {formula}")
            imgui.spacing()
            imgui.text(f"Total de Átomos: {len(state.selected_mol)}")
            imgui.spacing()
            imgui.text_disabled("(Clic para volver a inspección simple)")
            imgui.text_disabled("Estructura resaltada en Cian Eléctrico.")

        imgui.spacing()
        if imgui.button("CERRAR INSPECTOR", imgui.ImVec2(-1, 0)):
            state.selected_idx = -1
            state.selected_mol = []
        imgui.end()

    # --- HUD DE CÁMARA DINÁMICO ---
    UIWidgets.camera_hud(state.camera, win_w, win_h)

def update():
    # 0. Sincronización crucial Taichi -> CPU -> GL
    ti.sync()
    
    io = imgui.get_io()
    dt = io.delta_time
    
    # --- GESTIÓN DE ACELERACIÓN Y PAUSA INTELIGENTE ---
    if not io.want_capture_keyboard:
        t_now = time.time()
        
        # 1. Pausa Estándar [Espacio]
        if imgui.is_key_pressed(imgui.Key.space):
            state.paused = not state.paused
            state.time_scale = 0.0 if state.paused else 1.0
            state.add_log(f"SISTEMA: {'Pausado' if state.paused else 'Reanudado'}")

        # 2. Pedal de Aceleración [Tab]
        if imgui.is_key_pressed(imgui.Key.tab):
            # Detectar Doble Tap (Pausa)
            if (t_now - state.last_tab_time) < 0.3:
                state.paused = not state.paused
                state.time_scale = 0.0 if state.paused else 1.0
                state.add_log("SISTEMA: Toggle Pausa (Doble Tab)")
            state.last_tab_time = t_now

        if imgui.is_key_down(imgui.Key.tab):
            if not state.boost_active:
                state.boost_active = True
                state.add_log("BOOST: Acelerando evolución...")
            
            # Aceleración gradual (tipo pedal)
            accel_rate = 10.0 * dt # Aumenta 10 unidades por segundo
            state.time_scale = min(UIConfig.BOOST_SPEED, state.time_scale + accel_rate)
            state.pause_timer = 0 
        
        # Al soltar TAB: Retorno Óptimo (1.0x) con pequeña estabilización
        elif state.boost_active:
            state.boost_active = False
            state.time_scale = 0.0 # Breve pausa
            state.pause_timer = 0.5 # Estabilización corta
            state.add_log("SISTEMA: Retorno a Velocidad Óptima.")
            
    # Manejar temporizador de pausa (Restaurar a 1.0x)
    if state.pause_timer > 0:
        state.pause_timer -= dt
        if state.pause_timer <= 0:
            state.time_scale = 1.0 # SIEMPRE vuelve a 1.0x (Velocidad Óptima)
            state.paused = False

    # Petición: Cambiar Debug con F3
    if imgui.is_key_pressed(imgui.Key.f3):
        state.show_debug = not state.show_debug
        print(f"[UI] Debug Toggle: {state.show_debug}")

    display_size = io.display_size
    w, h = int(display_size.x), int(display_size.y)
    
    # 0.1 Actualización de Cámara
    if w > 0 and h > 0:
        if not hasattr(state, '_diag_done'):
            print(f"[WINDOW] Res actual: {w}x{h}")
            # Importar n_particles aquí si no es global
            print(f"[SIM] Partículas activas: {n_particles[None]}")
            state._diag_done = True
        
        state.camera.update_aspect(w, h)
        
        # 0.2 Input Handling (Cámara)
        if not io.want_capture_mouse:
            if imgui.is_mouse_dragging(imgui.MouseButton_.middle):
                delta = io.mouse_delta
                vis_w, vis_h = state.camera.get_visible_area()
                move_x = -delta.x * (vis_w / w)
                move_y = -delta.y * (vis_h / h)
                state.camera.move(move_x, move_y)
            
            wheel = io.mouse_wheel
            if wheel != 0:
                zoom_factor = 1.15 if wheel > 0 else 0.85
                state.camera.update_zoom(zoom_factor)

            # --- INTERACCIÓN: Click para Selección o Onda de Choque ---
            if imgui.is_mouse_clicked(imgui.MouseButton_.left):
                mx, my = io.mouse_pos.x, io.mouse_pos.y
                world_x, world_y = state.camera.screen_to_world(mx, my, w, h)
                
                # Sincronización leve para leer posiciones
                p_pos = pos.to_numpy()
                p_active = is_active.to_numpy()
                
                # Buscar el más cercano
                dists_sq = np.sum((p_pos - np.array([world_x, world_y]))**2, axis=1)
                dists_sq[~is_active.to_numpy().astype(bool)] = 1e12
                
                idx = np.argmin(dists_sq)
                
                # Radio interactivo dinámico (Escalado por Zoom)
                # Queremos que el área de clic sea proporcional a lo que se ve en pantalla
                vis_h = WORLD_SIZE / state.camera.zoom
                world_px = vis_h / h # Unidades de mundo por píxel
                # Detección: El radio del punto (30px / 2) + margen de 10px = 25px
                detect_rad = 25.0 * world_px 
                
                if dists_sq[idx] < detect_rad**2:
                    # SELECCIÓN: Ciclo Átomo -> Molécula -> Deselección
                    if state.selected_idx == idx:
                        if not state.selected_mol:
                            # 2do Click: Expandir a molécula
                            state.selected_mol = state.get_molecule_indices(idx)
                            print(f"[PICK] Molécula detectada: {len(state.selected_mol)} átomos.")
                        else:
                            # 3er Click: Deseleccionar
                            state.selected_idx = -1
                            state.selected_mol = []
                    else:
                        # 1er Click: Nuevo átomo
                        state.selected_idx = idx
                        state.selected_mol = []
                        print(f"[PICK] Átomo detectado: {idx}")
                else:
                    # Click en vacío: Deseleccionar todo
                    state.selected_idx = -1
                    state.selected_mol = []

            # ONDA DE CHOQUE: Solo con CTRL (Separación total de eventos) 🧬
            if imgui.is_mouse_clicked(imgui.MouseButton_.left) and io.key_ctrl:
                mx, my = io.mouse_pos.x, io.mouse_pos.y
                world_x, world_y = state.camera.screen_to_world(mx, my, w, h)
                apply_force_pulse(world_x, world_y, 2.5)
                print(f"[PWR] Pulso de Fuerzas (CTRL+Click) en Mundo: [{world_x:.1f}, {world_y:.1f}]")
    margin_culling = 500.0 # Más amplio para evitar parpadeos
    b = state.camera.get_culling_bounds(margin_culling)
    sim_bounds[0], sim_bounds[1] = float(b[0]), float(b[1])
    sim_bounds[2], sim_bounds[3] = float(b[2]), float(b[3])
    if not state.paused:
        now = time.time()
        dt = now - state.last_time
        if dt > 0:
            state.fps = 0.9 * state.fps + 0.1 * (1.0 / dt)
        state.last_time = now
        
        # Sincronizar escala de tiempo desde configuración si es necesario
        # state.time_scale se controla desde el slider de la UI
        
        steps = int(state.time_scale)
        if np.random.random() < (state.time_scale - steps):
            steps += 1
            
        if steps > 0:
            # Re-evaluar selección dinámica si hay cambios en el mundo
            if state.selected_idx >= 0 and state.selected_mol:
                state.selected_mol = state.get_molecule_indices(state.selected_idx)
            
            # Monitorear conteo de enlaces y eventos evolutivos
            prev_bonds = total_bonds_count[None]
            prev_mutations = total_mutations[None]
            prev_tunnels = total_tunnels[None]
            
            run_simulation_fast(steps)
            
            # Verificación ocasional de cambios para el log
            new_bonds = total_bonds_count[None]
            new_mutations = total_mutations[None]
            new_tunnels = total_tunnels[None]
            
            if new_bonds > prev_bonds:
                diff = new_bonds - prev_bonds
                state.stats["bonds_formed"] += diff
                state.add_log(f"ENLACE: +{diff} uniones químicas.")
            elif new_bonds < prev_bonds:
                diff = prev_bonds - new_bonds
                state.stats["bonds_broken"] += diff
                state.add_log(f"ROTURA: {diff} enlaces disueltos.")
            
            if new_mutations > prev_mutations:
                diff = new_mutations - prev_mutations
                state.stats["mutations"] += diff
                state.add_log(f"CATÁLISIS: {diff} átomos activos.")
            
            if new_tunnels > prev_tunnels:
                diff = new_tunnels - prev_tunnels
                state.stats["tunnels"] += diff
                state.add_log(f"TRANSICIÓN: {diff} saltos de energía.")

    update_grid()
    ti.sync() # Asegurar que Taichi terminó la simulación antes de renderizar
    zoom, cx, cy = state.camera.get_render_params()
    aspect = state.camera.aspect_ratio
    update_borders_gl(zoom, cx, cy, aspect)
    prepare_bond_lines_gl(zoom, cx, cy, aspect)
    n_vis = n_visible[None]
    if not hasattr(state, '_diag_vis_done') and n_vis > 0:
        print(f"[SIM] Visibles iniciales: {n_vis}")
        state._diag_vis_done = True

    if n_vis > 0:
        pos_np = pos.to_numpy()
        col_np = colors.to_numpy()
        vis_indices = visible_indices.to_numpy()[:n_vis]
        pos_vis = pos_np[vis_indices]
        col_vis = col_np[vis_indices]
        vis_h_half = WORLD_SIZE / (2.0 * zoom)
        vis_w_half = vis_h_half * aspect
        pos_gl = np.zeros((len(pos_vis), 2), dtype=np.float32)
        pos_gl[:, 0] = (pos_vis[:, 0] - cx) / vis_w_half
        pos_gl[:, 1] = -(pos_vis[:, 1] - cy) / vis_h_half
        bonds_gl = bond_vertices.to_numpy()[:n_bond_vertices[None]].astype(np.float32)
        debug_gl = None
        if state.show_debug:
            b_box = border_vertices.to_numpy()
            s_box = screen_box_vertices.to_numpy()
            debug_gl = np.vstack([b_box, s_box]).astype(np.float32)

        # --- GENERAR COORDENADAS PARA HIGHLIGHTS (Jerarquía Cian/Blanco) ---
        highlight_gl = None
        if state.selected_idx >= 0:
            h_list = []
            
            # El radio visual del átomo es ~15px. Queremos que el borde esté a 17-18px.
            # En NDC X (1280px), 18px es 18/640 = 0.028
            def add_circle(center_pos, r_gl=UIConfig.HIGHLIGHT_RADIUS, segments=UIConfig.HIGHLIGHT_SEGMENTS, as_lines=False):
                cx_gl = (center_pos[0] - cx) / vis_w_half
                cy_gl = -(center_pos[1] - cy) / vis_h_half
                verts = []
                for i in range(segments):
                    angle = 2.0 * math.pi * i / segments
                    verts.append((cx_gl + r_gl * math.cos(angle), 
                                  cy_gl + r_gl * math.sin(angle) * aspect))
                if as_lines:
                    for i in range(segments):
                        h_list.extend(verts[i]); h_list.extend(verts[(i+1)%segments])
                else:
                    for v in verts: h_list.extend(v)

            # 1. Átomo Foco (Blanco)
            add_circle(pos_np[state.selected_idx], UIConfig.HIGHLIGHT_RADIUS, UIConfig.HIGHLIGHT_SEGMENTS, as_lines=False)
            
            all_enlaces_np = enlaces_idx.to_numpy()
            n_enlaces_np = num_enlaces.to_numpy()
            
            if not state.selected_mol:
                # MODO ÁTOMO: Resaltar solo vecinos inmediatos ("Hermanos")
                n_count = n_enlaces_np[state.selected_idx]
                for i in range(n_count):
                    neighbor = all_enlaces_np[state.selected_idx, i]
                    if neighbor >= 0:
                        # Círculo sutil para el hermano
                        add_circle(pos_np[neighbor], UIConfig.HIGHLIGHT_RADIUS, UIConfig.HIGHLIGHT_SEGMENTS, as_lines=True)
                        # Enlace al hermano
                        mp = pos_np[state.selected_idx]
                        np_p = pos_np[neighbor]
                        h_list.extend([(mp[0]-cx)/vis_w_half, -(mp[1]-cy)/vis_h_half, 
                                       (np_p[0]-cx)/vis_w_half, -(np_p[1]-cy)/vis_h_half])
            else:
                # MODO MOLÉCULA: Resaltar todo el conjunto (Cian)
                mol_set = set(state.selected_mol)
                for m_idx in state.selected_mol:
                    if m_idx != state.selected_idx:
                        add_circle(pos_np[m_idx], UIConfig.HIGHLIGHT_RADIUS, UIConfig.HIGHLIGHT_SEGMENTS, as_lines=True)
                    
                    # Enlaces de la estructura
                    mp = pos_np[m_idx]
                    mpx, mpy = (mp[0]-cx)/vis_w_half, -(mp[1]-cy)/vis_h_half
                    for i in range(n_enlaces_np[m_idx]):
                        neighbor = all_enlaces_np[m_idx, i]
                        if neighbor in mol_set and neighbor > m_idx: 
                            np_p = pos_np[neighbor]
                            npx, npy = (np_p[0]-cx)/vis_w_half, -(np_p[1]-cy)/vis_h_half
                            h_list.extend([mpx, mpy, npx, npy])
            
            highlight_gl = np.array(h_list, dtype=np.float32)

        state.renderer.render(pos_gl, col_vis, bonds_gl, debug_gl, highlight_gl, w, h)
    else:
        state.renderer.ctx.viewport = (0, 0, w, h)
        state.renderer.ctx.clear(0.02, 0.02, 0.05, 1.0) 

def main():
    params = immapp.RunnerParams()
    params.callbacks.show_gui = gui
    params.callbacks.custom_background = update
    params.app_window_params.window_title = "QuimicPYTHON - Motor OpenGL Pro"
    params.app_window_params.window_geometry.size = (1024, 600) # Más corto para evitar problemas con la X
    params.app_window_params.restore_previous_geometry = False
    # Forzar posición centrada en monitor 0
    params.app_window_params.window_geometry.monitor_idx = 0
    params.app_window_params.window_geometry.position_mode = hello_imgui.WindowPositionMode.monitor_center
    
    def init_moderngl():
        try:
            # Forzar creación de contexto ModernGL compartiendo el actual
            ctx = moderngl.create_context()
            state.renderer = ParticleRenderer(ctx)
            print(f"[RENDER] Contexto ModernGL {ctx.version_code} via {ctx.info['GL_RENDERER']} listo.")
            print(f"[RENDER] Fabricante: {ctx.info['GL_VENDOR']}")
        except Exception as e:
            print(f"[CRITICAL] Error al crear contexto ModernGL: {e}")

    params.callbacks.post_init = init_moderngl
    params.imgui_window_params.default_imgui_window_type = hello_imgui.DefaultImGuiWindowType.no_default_window
    immapp.run(params)

if __name__ == "__main__":
    main()
