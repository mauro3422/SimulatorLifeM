import taichi as ti
import numpy as np
import moderngl
import imgui_bundle
from imgui_bundle import immapp, hello_imgui, imgui
import glfw  # NECESARIO PARA VSYNC
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
    total_mutations, total_tunnels, total_bonds_count, n_simulated_physics,
    charge_factor, universal_gpu_buffer, MAX_BONDS,
    pos_z,  # 2.5D depth field
    molecule_id  # m Molecule ID
)
import src.config as cfg
from src.core.context import get_context
from src.renderer.camera import Camera
from src.renderer.particle_renderer import ParticleRenderer
from src.ui.panels.molecular_analysis_panel import draw_molecular_analysis_panel, run_molecular_analysis_tick
from src.renderer.opengl_kernels import (
    update_borders_gl, prepare_bond_lines_gl,
    MAX_BOND_VERTICES, MAX_HIGHLIGHTS,
    OFFSET_STATS, OFFSET_PARTICLES, OFFSET_BONDS, OFFSET_HIGHLIGHTS, OFFSET_DEBUG,
    universal_gpu_buffer, compact_render_data, prepare_highlights
)
from src.core.input_handler import InputHandler
from src.ui.panels import draw_control_panel, draw_telemetry_panel, draw_monitor_panel, draw_inspector_panel
from src.ui.panels.quimidex_panel import draw_quimidex_panel
from src.ui.atom_labels import draw_atom_labels
from src.ui.bubble_labels import draw_bubble_labels
from src.ui.player_indicator import draw_player_indicator
from src.core.perf_logger import get_perf_logger
from src.core.frame_loop import FrameLoop

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
    'molecule_id': molecule_id,  # Nuevo campo para Highlight Rápido
    
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
        'vel': vel,  # Añadido para movimiento del jugador
        'is_active': is_active,
        'apply_force_pulse': apply_force_pulse,
        'enlaces_idx': enlaces_idx,  # Añadido para force_bond
        'num_enlaces': num_enlaces,  # Añadido para force_bond
        'manos_libres': manos_libres,  # Añadido para force_bond
        'atom_types': atom_types,  # Añadido para evolución
        'molecule_id': molecule_id, # Añadido
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

# GPU Resources para inyección en FrameLoop
gpu_resources = {
    'sim_bounds': sim_bounds,
    'run_simulation_fast': run_simulation_fast,
    'update_borders_gl': update_borders_gl,
    'prepare_bond_lines_gl': prepare_bond_lines_gl,
    'compact_render_data': compact_render_data,
    'prepare_highlights': prepare_highlights,
    'universal_gpu_buffer': universal_gpu_buffer,
    'n_particles': n_particles,
    'pos': pos,
    'pos_z': pos_z,  # 2.5D depth for visualization
    'num_enlaces': num_enlaces,
    'enlaces_idx': enlaces_idx,
    'atom_types': atom_types,  # Agregado para sync unificado
    'molecule_id': molecule_id, # Agregado para sync unificado
    'is_active': is_active,    # Agregado para sync unificado
}

# Render offsets para FrameLoop
render_resources = {
    'OFFSET_STATS': OFFSET_STATS,
    'OFFSET_PARTICLES': OFFSET_PARTICLES,
    'OFFSET_BONDS': OFFSET_BONDS,
    'OFFSET_HIGHLIGHTS': OFFSET_HIGHLIGHTS,
    'OFFSET_DEBUG': OFFSET_DEBUG,
}

# Crear FrameLoop
frame_loop = FrameLoop(state, gpu_resources, render_resources)


def gui():
    """Función principal de UI - Delega a módulos de paneles."""
    perf = get_perf_logger()
    perf.start("ui")
    
    io = imgui.get_io()
    display_size = io.display_size
    win_w, win_h = display_size.x, display_size.y

    # Toggle Quimidex con 'P'
    if imgui.is_key_pressed(imgui.Key.p):
        state.show_quimidex[0] = not state.show_quimidex[0]
    
    # Panel de Control (Izquierda)
    draw_control_panel(state, physics_controls, win_h)
    
    # Panel de Telemetría F3 (Derecha superior - condicional)
    # Usamos getattr para evitar crash en primer frame y evitar n_visible[None] (GPU sync)
    sim_count = getattr(state, 'n_simulated_val', 0)
    vis_count = getattr(state, 'n_visible_val', 0)
    draw_telemetry_panel(state, vis_count, sim_count, win_w)
    
    # Monitor de Actividad Molecular (Derecha)
    draw_monitor_panel(state, state.show_debug, win_w)
    
    # Inspector Molecular (Inferior izquierda - condicional)
    # ExtraerSynced data from last frame
    synced_current = state.render_data.get('synced') if hasattr(state, 'render_data') else None
    draw_inspector_panel(state, synced_current, win_h)
    
    # Enciclopedia Molecular (Quimidex) - Toggle 'P'
    draw_quimidex_panel(state, state.show_quimidex)
    
    # Panel de Análisis Molecular (Izquierda inferior)
    # Toggle con tecla 'F4' (cambiado de 'A' para liberar WASD)
    if imgui.is_key_pressed(imgui.Key.f4):
        if not hasattr(state, 'show_mol_analysis'):
            state.show_mol_analysis = False
        state.show_mol_analysis = not state.show_mol_analysis
    
    if getattr(state, 'show_mol_analysis', False):
        draw_molecular_analysis_panel(state)


    # HUD de Cámara (Centro inferior)
    UIWidgets.camera_hud(state.camera, win_w, win_h)
    
    # Etiquetas - Toggle con L
    if state.show_labels and hasattr(state, 'render_data') and state.render_data:
        rd = state.render_data
        
        # Obtener zoom actual para decidir qué tipo de etiquetas mostrar
        zoom, _, _ = state.camera.get_render_params()
        
        # Umbral: zoom > threshold = Átomos, zoom < threshold = Moléculas
        if zoom < state.lod_threshold and rd.get('lod_bubbles'):
             # ZOOM ALEJADO: Etiquetas de fórmula molecular
             from src.ui.bubble_labels import draw_bubble_labels
             draw_bubble_labels(
                 rd.get('lod_bubbles'),
                 state.camera.get_render_params_label(),
                 win_w, win_h,
                 alpha=1.0
             )
        else:
             # ZOOM CERCANO: Etiquetas por átomo (H, C, O...)
             if rd.get('pos_vis') is not None and rd.get('type_vis') is not None:
                from src.ui.atom_labels import draw_atom_labels
                n_vis = rd.get('n_vis', 0)
                draw_atom_labels(
                    rd['pos_vis'],
                    rd['type_vis'],
                    None,
                    n_vis,
                    state.camera.get_render_params_label(),
                    win_w, win_h,
                    show_labels=True,
                    alpha=1.0
                )
    
    # Indicador de Jugador (Atomic Farmer) - Siempre visible
    # Animación: soporta spreadsheets si total_frames > 1
    total_frames = 1 
    current_frame = int(time.time() * 8.0) % total_frames
    
    draw_player_indicator(
        state.player_idx,
        pos,
        state.camera.get_render_params_label(),
        win_w, win_h,
        frame_idx=current_frame,
        total_frames=total_frames
    )
    
    # --- HUD JUGADOR (METABOLISMO Y MISIONES) ---
    draw_list = imgui.get_foreground_draw_list()
    
    # 1. Barra de ATP (Esquina superior izquierda)
    atp_ratio = state.atp / state.progression.max_atp
    atp_col = imgui.IM_COL32(200, 200, 50, 200) if atp_ratio > 0.3 else imgui.IM_COL32(255, 50, 50, 255)
    
    # Fondo de la barra
    draw_list.add_rect_filled(imgui.ImVec2(10, 10), imgui.ImVec2(210, 30), imgui.IM_COL32(30, 30, 30, 200), 5.0)
    # Relleno
    draw_list.add_rect_filled(imgui.ImVec2(12, 12), imgui.ImVec2(12 + (196 * atp_ratio), 28), atp_col, 3.0)
    # Texto
    draw_list.add_text(imgui.ImVec2(15, 12), imgui.IM_COL32(255, 255, 255, 255), f"ENERGIA (ATP): {state.atp:.1f}")
    
    # 2. Misión Actual (Centro superior)
    mission_text = state.progression.get_status_text()
    if getattr(state.progression, 'in_clay', False):
        mission_text += " [ ARCILLA DETECTADA ]"
        
    m_size = imgui.calc_text_size(mission_text)
    mx, my = (win_w - m_size.x) * 0.5, 10
    
    # Fondo con estilo glassmorphism (Color ocre si está en arcilla)
    bg_col = imgui.IM_COL32(100, 80, 20, 180) if getattr(state.progression, 'in_clay', False) else imgui.IM_COL32(0, 0, 0, 160)
    draw_list.add_rect_filled(imgui.ImVec2(mx - 15, my - 5), imgui.ImVec2(mx + m_size.x + 15, my + m_size.y + 10), bg_col, 10.0)
    draw_list.add_rect(imgui.ImVec2(mx - 15, my - 5), imgui.ImVec2(mx + m_size.x + 15, my + m_size.y + 10), imgui.IM_COL32(100, 255, 100, 150), 10.0, thickness=1.5)
    
    draw_list.add_text(imgui.ImVec2(mx, my + 2), imgui.IM_COL32(100, 255, 100, 255), mission_text)
    
    # 3. Buffs Activos (Debajo de la barra de ATP)
    if hasattr(state.progression, 'active_buffs') and state.progression.active_buffs:
        buff_text = "Buffs: " + ", ".join(state.progression.active_buffs)
        draw_list.add_text(imgui.ImVec2(10, 40), imgui.IM_COL32(255, 215, 0, 255), buff_text)

    perf.stop("ui")


def update():
    """
    Función principal de actualización.
    Sincroniza el estado con la GPU y corre la simulación.
    """
    # 1. Sincronizar parámetros dinámicos (Buffs, Arcilla) a la GPU
    state.sync_to_gpu()
    
    # 2. Actualizar Progresión (ATP, Misiones, Ubicación del jugador)
    # delta_time aproximado para la lógica de metabolismo
    dt = 1.0 / 60.0 
    state.progression.update(dt)

    perf = get_perf_logger()
    perf.start("ui")
    
    io = imgui.get_io()
    display_size = io.display_size
    fb_scale = io.display_framebuffer_scale
    
    # Manejo correcto de High-DPI (Retina/4K)
    # Window size (Logical) vs Framebuffer size (Physical)
    win_w, win_h = int(display_size.x), int(display_size.y)
    fb_w, fb_h = int(display_size.x * fb_scale.x), int(display_size.y * fb_scale.y)
    
    # Input handling usa coordenadas lógicas (Window)
    input_handler.process_all(io, win_w, win_h, WORLD_SIZE)
    perf.stop("ui")
    
    # Diagnóstico inicial (una sola vez)
    # Diagnóstico inicial (una sola vez)
    if win_w > 0 and win_h > 0 and not hasattr(state, '_diag_done'):
        print(f"[WINDOW] Res actual: {win_w}x{win_h}")
        print(f"[SIM] Partículas activas: {n_particles[None]}")
        state._diag_done = True
    
    # Frame loop
    frame_data = frame_loop.tick(io, WORLD_SIZE, override_res=(fb_w, fb_h))
    
    # Análisis molecular (cada 30 frames)
    run_molecular_analysis_tick(state)
    
    # Render (solo si el renderer ya está inicializado en post_init)
    if getattr(state, 'renderer') is not None:
        frame_loop.render_frame(frame_data, WORLD_SIZE)

def main():
    perf = get_perf_logger()
    
    # Init Globals
    charge_factor[None] = 125.0 # Reactivado con Amortización (Interleaved)
    print("[INIT] Charge Factor set to 125.0 (Optimized)")
    
    params = immapp.RunnerParams()
    params.callbacks.show_gui = gui
    params.callbacks.custom_background = update
    params.app_window_params.window_title = "QuimicPYTHON - Motor OpenGL Pro"
    params.app_window_params.window_geometry.size = (1024, 600)
    params.app_window_params.restore_previous_geometry = False
    params.app_window_params.window_geometry.monitor_idx = 0
    params.app_window_params.window_geometry.position_mode = hello_imgui.WindowPositionMode.monitor_center
    
    # Desbloquear FPS (0 = Sin límite / VSync nativo)
    params.fps_idling.enable_idling = False
    params.fps_idling.fps_idle = 0
    
    
    def init_moderngl():
        try:
            # 1. Configurar Contexto ModernGL
            ctx = moderngl.create_context()
            state.renderer = ParticleRenderer(ctx, MAX_PARTICLES, MAX_BOND_VERTICES)
            
            # Iniciar worker de química asíncrona
            from src.systems.async_chemistry import start_async_chemistry
            start_async_chemistry()
            
            # Aplicar estilo de UI ahora que el contexto existe
            UIConfig.apply_style()
            
            print(f"[RENDER] Contexto ModernGL {ctx.version_code} via {ctx.info['GL_RENDERER']} listo.")

            print(f"[RENDER] Fabricante: {ctx.info['GL_VENDOR']}")
            
            # 2. INTENTO DE FUERZA BRUTA: Desactivar VSync (Swap Interval 0)
            try:
                glfw.swap_interval(0)
                print("[INIT] VSync desactivado manualmente (glfw.swap_interval(0))")
            except Exception as e_vsync:
                print(f"[WARN] No se pudo desactivar VSync: {e_vsync}")
                
        except Exception as e:
            print(f"[CRITICAL] Error al crear contexto ModernGL: {e}")
    
    def on_exit():
        """Callback al cerrar la aplicación - guarda métricas e inventario."""
        # Detener worker async de química
        from src.systems.async_chemistry import stop_async_chemistry
        stop_async_chemistry()
        
        from src.gameplay.inventory import get_inventory
        get_inventory().save()
        
        perf.print_summary()
        perf.save_session()


    params.callbacks.post_init = init_moderngl
    params.callbacks.before_exit = on_exit
    params.imgui_window_params.default_imgui_window_type = hello_imgui.DefaultImGuiWindowType.no_default_window
    immapp.run(params)

if __name__ == "__main__":
    main()

