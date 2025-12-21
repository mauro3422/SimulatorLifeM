"""
DearPyGui UI Module - QuimicPYTHON
===================================
Nueva UI basada en DearPyGui con raw_texture para rendering en tiempo real.
"""
import dearpygui.dearpygui as dpg
import numpy as np

# Constantes de UI
VIEWPORT_WIDTH = 1200
VIEWPORT_HEIGHT = 700
# DEBE coincidir con RENDER_WIDTH/HEIGHT de kernel_renderer.py
SIM_DISPLAY_WIDTH = 600  
SIM_DISPLAY_HEIGHT = 500

class SimulatorUI:
    """Clase principal de UI con DearPyGui."""
    
    def __init__(self):
        self.texture_tag = None
        self.texture_data = None
        self.show_debug = True
        self.show_help = False
        
        # Callbacks externos (se setean desde main)
        self.on_speed_change = None
        self.on_pause = None
        self.on_reset = None
        self.on_shake = None
        self.on_zoom_change = None
        
        # Estado
        self.time_scale = 2.0
        self.is_paused = False
        self.zoom = 2.5
        
        # Stats para mostrar
        self.fps = 0
        self.active_particles = 0
        self.total_particles = 0
        self.sim_frame = 0
        self.events = []
    
    def setup(self):
        """Inicializa DearPyGui."""
        dpg.create_context()
        
        # Crear textura DINAMICA para la simulacion (mejor para updates frecuentes)
        self.texture_data = np.zeros((SIM_DISPLAY_HEIGHT, SIM_DISPLAY_WIDTH, 4), dtype=np.float32)
        # Llenar con gris para test
        self.texture_data[:, :, :3] = 0.2
        self.texture_data[:, :, 3] = 1.0
        
        with dpg.texture_registry():
            self.texture_tag = dpg.add_dynamic_texture(
                width=SIM_DISPLAY_WIDTH,
                height=SIM_DISPLAY_HEIGHT,
                default_value=self.texture_data.flatten().tolist()
            )
        
        # Crear ventana principal
        with dpg.window(label="QuimicPYTHON", tag="main_window", no_close=True):
            with dpg.group(horizontal=True):
                # Panel izquierdo: Simulacion
                with dpg.child_window(width=SIM_DISPLAY_WIDTH + 20, height=SIM_DISPLAY_HEIGHT + 40):
                    dpg.add_text("Simulacion GPU (Vulkan)")
                    dpg.add_image(self.texture_tag)
                
                # Panel derecho: Controles
                with dpg.child_window(width=350, height=SIM_DISPLAY_HEIGHT + 40):
                    self._create_control_panel()
            
            # Panel inferior: Debug/Timeline
            with dpg.child_window(height=150, tag="bottom_panel"):
                self._create_debug_panel()
        
        # Configurar viewport
        dpg.create_viewport(
            title="QuimicPYTHON - Simulador de Vida",
            width=VIEWPORT_WIDTH,
            height=VIEWPORT_HEIGHT
        )
        dpg.setup_dearpygui()
        dpg.set_primary_window("main_window", True)
        
        # Registrar handlers de teclado
        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_Q, callback=self._on_key_q)
            dpg.add_key_press_handler(dpg.mvKey_E, callback=self._on_key_e)
            dpg.add_key_press_handler(dpg.mvKey_P, callback=self._on_key_p)
            dpg.add_key_press_handler(dpg.mvKey_R, callback=self._on_key_r)
            dpg.add_key_press_handler(dpg.mvKey_G, callback=self._on_key_g)
            dpg.add_key_press_handler(dpg.mvKey_I, callback=self._on_key_i)
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=self._on_key_esc)
    
    def _create_control_panel(self):
        """Crea el panel de controles."""
        dpg.add_text("=== CONTROLES ===", color=(150, 200, 255))
        dpg.add_separator()
        
        # Velocidad
        dpg.add_text("Velocidad de Simulacion:")
        dpg.add_slider_float(
            tag="speed_slider",
            default_value=self.time_scale,
            min_value=0.0,
            max_value=10.0,
            callback=self._on_speed_slider,
            width=200
        )
        dpg.add_text("[Q] + | [E] - | [P] Pausa", color=(100, 100, 100))
        
        dpg.add_spacer(height=10)
        
        # Zoom
        dpg.add_text("Zoom:")
        dpg.add_slider_float(
            tag="zoom_slider",
            default_value=self.zoom,
            min_value=1.0,
            max_value=15.0,
            callback=self._on_zoom_slider,
            width=200
        )
        
        dpg.add_spacer(height=10)
        dpg.add_separator()
        
        # Botones
        dpg.add_button(label="Agitar Simulacion", callback=self._on_shake_btn, width=200)
        dpg.add_button(label="Reiniciar Mundo [R]", callback=self._on_reset_btn, width=200)
        
        dpg.add_spacer(height=20)
        dpg.add_separator()
        
        # Checkboxes
        dpg.add_checkbox(label="Mostrar Debug [G]", tag="debug_check", default_value=True, callback=self._on_debug_toggle)
        dpg.add_checkbox(label="Mostrar Ayuda [I]", tag="help_check", default_value=False, callback=self._on_help_toggle)
        
        dpg.add_spacer(height=20)
        
        # Info
        dpg.add_text("=== ROADMAP ===", color=(200, 180, 100))
        dpg.add_text("Fase 1: Quimica avanzada", bullet=True)
        dpg.add_text("Fase 2: Proto-bioquimica", bullet=True)
        dpg.add_text("Fase 3: Vida emergente", bullet=True)
        dpg.add_text("Fase 4: Narracion LLM", bullet=True)
    
    def _create_debug_panel(self):
        """Crea el panel de debug/timeline."""
        with dpg.group(horizontal=True):
            # Timeline
            with dpg.child_window(width=300, tag="timeline_panel"):
                dpg.add_text("=== TIMELINE ===", color=(100, 255, 150))
                dpg.add_text("Frame: 0", tag="frame_text")
                dpg.add_text("FPS: 0", tag="fps_text")
                dpg.add_text("Estado: Activo", tag="state_text")
            
            # Stats
            with dpg.child_window(width=300, tag="stats_panel"):
                dpg.add_text("=== ESTADISTICAS ===", color=(255, 200, 100))
                dpg.add_text("Particulas: 0/0", tag="particles_text")
                dpg.add_text("Zoom: 2.5x", tag="zoom_text")
            
            # Eventos
            with dpg.child_window(width=350, tag="events_panel"):
                dpg.add_text("=== EVENTOS RECIENTES ===", color=(200, 150, 255))
                dpg.add_text("(Sin eventos)", tag="events_text")
    
    def update_texture(self, pos_data, colors_data, n_particles):
        """Renderiza partículas directamente en CPU y actualiza textura."""
        # Usar buffer persistente para evitar re-allocacion
        if not hasattr(self, '_frame_buffer') or self._frame_buffer is None:
            self._frame_buffer = np.zeros((SIM_DISPLAY_HEIGHT, SIM_DISPLAY_WIDTH, 4), dtype=np.float32)
        
        frame = self._frame_buffer
        
        # Limpiar frame (fondo azul oscuro)
        frame[:, :, 0] = 0.02
        frame[:, :, 1] = 0.02
        frame[:, :, 2] = 0.05
        frame[:, :, 3] = 1.0
        
        # Dibujar partículas (optimizado: solo dibujar si posicion es valida)
        for i in range(min(n_particles, 5000)):
            px = pos_data[i, 0]
            py = pos_data[i, 1]
            
            # Saltar partículas fuera de pantalla
            if px <= 0 or px >= 1 or py <= 0 or py >= 1:
                continue
            
            # Convertir a pixels
            x = int(px * SIM_DISPLAY_WIDTH)
            y = int((1.0 - py) * SIM_DISPLAY_HEIGHT)
            
            # Bounds check rapido
            if x < 3 or x >= SIM_DISPLAY_WIDTH - 3 or y < 3 or y >= SIM_DISPLAY_HEIGHT - 3:
                continue
            
            # Color
            r, g, b = colors_data[i, 0], colors_data[i, 1], colors_data[i, 2]
            
            # Dibujar circulo de 2 pixels (mas rapido)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx*dx + dy*dy <= 4:
                        frame[y + dy, x + dx, 0] = r
                        frame[y + dy, x + dx, 1] = g
                        frame[y + dy, x + dx, 2] = b
        
        # Enviar a DearPyGui (flatten + tolist es inevitable pero buffer persistente ayuda)
        dpg.set_value(self.texture_tag, frame.flatten().tolist())
    
    def update_stats(self, fps, active, total, frame, events=None):
        """Actualiza los stats mostrados."""
        self.fps = fps
        self.active_particles = active
        self.total_particles = total
        self.sim_frame = frame
        
        dpg.set_value("fps_text", f"FPS: {fps}")
        dpg.set_value("frame_text", f"Frame: {frame:,}")
        dpg.set_value("particles_text", f"Particulas: {active}/{total}")
        dpg.set_value("zoom_text", f"Zoom: {self.zoom:.1f}x")
        dpg.set_value("state_text", f"Estado: {'PAUSA' if self.is_paused else 'Activo'}")
        
        if events:
            events_str = "\n".join([f"  {e.description[:30]}" for e in events[-3:]])
            dpg.set_value("events_text", events_str if events_str else "(Sin eventos)")
    
    def render_frame(self):
        """Renderiza un frame de DearPyGui."""
        dpg.render_dearpygui_frame()
    
    def is_running(self):
        """Retorna True si la ventana sigue abierta."""
        return dpg.is_dearpygui_running()
    
    def show(self):
        """Muestra el viewport."""
        dpg.show_viewport()
    
    def cleanup(self):
        """Limpia recursos."""
        dpg.destroy_context()
    
    # --- Callbacks de teclado ---
    def _on_key_q(self):
        self.time_scale = min(10.0, self.time_scale + 0.5)
        dpg.set_value("speed_slider", self.time_scale)
        print(f"[SPEED] {self.time_scale:.1f}")
    
    def _on_key_e(self):
        self.time_scale = max(0.0, self.time_scale - 0.5)
        dpg.set_value("speed_slider", self.time_scale)
        print(f"[SPEED] {self.time_scale:.1f}")
    
    def _on_key_p(self):
        self.is_paused = not self.is_paused
        print(f"[TIMELINE] {'PAUSED' if self.is_paused else 'RESUMED'}")
    
    def _on_key_r(self):
        if self.on_reset:
            self.on_reset()
        print("[RESET] Mundo reiniciado")
    
    def _on_key_g(self):
        self.show_debug = not self.show_debug
        dpg.set_value("debug_check", self.show_debug)
    
    def _on_key_i(self):
        self.show_help = not self.show_help
        dpg.set_value("help_check", self.show_help)
    
    def _on_key_esc(self):
        dpg.stop_dearpygui()
    
    # --- Callbacks de UI ---
    def _on_speed_slider(self, sender, value):
        self.time_scale = value
    
    def _on_zoom_slider(self, sender, value):
        self.zoom = value
        if self.on_zoom_change:
            self.on_zoom_change(value)
    
    def _on_shake_btn(self):
        if self.on_shake:
            self.on_shake()
    
    def _on_reset_btn(self):
        if self.on_reset:
            self.on_reset()
    
    def _on_debug_toggle(self, sender, value):
        self.show_debug = value
    
    def _on_help_toggle(self, sender, value):
        self.show_help = value


def create_ui():
    """Factory function para crear la UI."""
    ui = SimulatorUI()
    ui.setup()
    return ui
