import taichi as ti
import numpy as np
import moderngl
from imgui_bundle import imgui, immapp, hello_imgui
import time
import math
import os

# Inicializar Taichi se delega a simulation_gpu
from src.config import UIConfig, UIWidgets
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
from src.renderer.particle_renderer import ParticleRenderer
from src.renderer.opengl_kernels import (
    update_borders_gl, prepare_bond_lines_gl,
    bond_vertices, n_bond_vertices, 
    border_vertices, screen_box_vertices,
    MAX_BOND_VERTICES
)
from src.core.input_handler import InputHandler
from src.ui.panels import draw_control_panel, draw_telemetry_panel, draw_monitor_panel, draw_inspector_panel
from src.core.perf_logger import get_perf_logger

# Constantes de mundo
WORLD_SIZE = cfg.sim_config.WORLD_SIZE

# ParticleRenderer moved to src/renderer/particle_renderer.py
# AppState moved to src/core/app_state.py

# Diccionario de campos de simulación para inyección de dependencias
simulation_fields = {
    # Campos de partículas
    'MAX_PARTICLES': MAX_PARTICLES,
    'n_particles': n_particles,
    'pos': pos,
    'radii': radii,
    'is_active': is_active,
    'atom_types': atom_types,
    'colors': colors,
    'manos_libres': manos_libres,
    
    # Campos de enlaces
    'enlaces_idx': enlaces_idx,
    'num_enlaces': num_enlaces,
    
    # Campos de física
    'gravity': gravity,
    'friction': friction,
    'temperature': temperature,
    'max_speed': max_speed,
    'world_width': world_width,
    'world_height': world_height,
    
    # Campos de enlaces (parámetros)
    'dist_equilibrio': dist_equilibrio,
    'spring_k': spring_k,
    'damping': damping,
    'rango_enlace_min': rango_enlace_min,
    'rango_enlace_max': rango_enlace_max,
    'dist_rotura': dist_rotura,
    'max_fuerza': max_fuerza,
    
    # Campos de interacción
    'prob_enlace_base': prob_enlace_base,
    'click_force': click_force,
    'click_radius': click_radius,
}

# Crear estado de aplicación usando contexto unificado
state = get_context()
state.init_camera(WORLD_SIZE, 1280, 720)
state.init_simulation(simulation_fields)

# InputHandler con referencias a datos de simulación
input_handler = InputHandler(
    state=state,
    simulation_data={
        'pos': pos,
        'is_active': is_active,
        'apply_force_pulse': apply_force_pulse
    }
)

# Physics controls para inyección en UI panels
physics_controls = {
    'gravity': gravity,
    'friction': friction,
    'temperature': temperature,
    'prob_enlace_base': prob_enlace_base,
    'rango_enlace_max': rango_enlace_max,
    'dist_rotura': dist_rotura
}


def gui():
    """Función principal de UI - Delega a módulos de paneles."""
    UIConfig.apply_style()
    
    io = imgui.get_io()
    display_size = io.display_size
    win_w, win_h = display_size.x, display_size.y
    
    # Panel de Control (Izquierda)
    draw_control_panel(state, physics_controls, win_h)
    
    # Panel de Telemetría F3 (Derecha superior - condicional)
    draw_telemetry_panel(state, n_visible[None], win_w)
    
    # Monitor de Actividad Molecular (Derecha)
    draw_monitor_panel(state, state.show_debug, win_w)
    
    # Inspector Molecular (Inferior izquierda - condicional)
    draw_inspector_panel(state, atom_types, win_h)
    
    # HUD de Cámara (Centro inferior)
    UIWidgets.camera_hud(state.camera, win_w, win_h)


def update():
    # Performance tracking
    perf = get_perf_logger()
    perf.start("total")
    
    # 0. Sincronización crucial Taichi -> CPU -> GL
    ti.sync()
    
    io = imgui.get_io()
    display_size = io.display_size
    w, h = int(display_size.x), int(display_size.y)
    
    # --- INPUT HANDLING (Delegado a InputHandler) ---
    input_handler.process_all(io, w, h, WORLD_SIZE)
    
    # Diagnóstico inicial (una sola vez)
    if w > 0 and h > 0 and not hasattr(state, '_diag_done'):
        print(f"[WINDOW] Res actual: {w}x{h}")
        print(f"[SIM] Partículas activas: {n_particles[None]}")
        state._diag_done = True
    
    # --- CULLING BOUNDS ---
    margin_culling = 500.0  # Más amplio para evitar parpadeos

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
    
    # Finalizar frame de performance
    perf.stop("total")
    perf.set_counter("particles_visible", n_visible[None])
    perf.set_counter("particles_active", n_particles[None])
    perf.set_counter("bonds_count", total_bonds_count[None])
    perf.end_frame(state.fps)

def main():
    perf = get_perf_logger()
    
    params = immapp.RunnerParams()
    params.callbacks.show_gui = gui
    params.callbacks.custom_background = update
    params.app_window_params.window_title = "QuimicPYTHON - Motor OpenGL Pro"
    params.app_window_params.window_geometry.size = (1024, 600)
    params.app_window_params.restore_previous_geometry = False
    params.app_window_params.window_geometry.monitor_idx = 0
    params.app_window_params.window_geometry.position_mode = hello_imgui.WindowPositionMode.monitor_center
    
    def init_moderngl():
        try:
            ctx = moderngl.create_context()
            state.renderer = ParticleRenderer(ctx, MAX_PARTICLES, MAX_BOND_VERTICES)
            print(f"[RENDER] Contexto ModernGL {ctx.version_code} via {ctx.info['GL_RENDERER']} listo.")
            print(f"[RENDER] Fabricante: {ctx.info['GL_VENDOR']}")
        except Exception as e:
            print(f"[CRITICAL] Error al crear contexto ModernGL: {e}")
    
    def on_exit():
        """Callback al cerrar la aplicación - guarda métricas de performance."""
        perf.print_summary()
        perf.save_session()

    params.callbacks.post_init = init_moderngl
    params.callbacks.before_exit = on_exit
    params.imgui_window_params.default_imgui_window_type = hello_imgui.DefaultImGuiWindowType.no_default_window
    immapp.run(params)

if __name__ == "__main__":
    main()

