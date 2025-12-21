"""
InputHandler - Gestión centralizada de entrada de teclado y mouse.
Extraído de main.py para modularización.
"""

import time
import numpy as np
from imgui_bundle import imgui
from src.config import UIConfig


class InputHandler:
    """Manejador de entrada de teclado y mouse para la simulación."""
    
    def __init__(self, state, simulation_data: dict):
        """
        Args:
            state: AppState instance containing simulation state
            simulation_data: Dict with 'pos', 'is_active', 'apply_force_pulse' references
        """
        self.state = state
        self.sim_data = simulation_data
        self.last_tab_time = 0.0
    
    def process_all(self, io, w: int, h: int, world_size: float):
        """
        Procesa todos los inputs del frame actual.
        
        Args:
            io: ImGui IO object
            w: Window width
            h: Window height  
            world_size: Size of the simulation world
        """
        dt = io.delta_time
        
        # Keyboard inputs
        if not io.want_capture_keyboard:
            self._process_keyboard(io, dt)
        
        # F3 Debug toggle (always available)
        if imgui.is_key_pressed(imgui.Key.f3):
            self.state.show_debug = not self.state.show_debug
            print(f"[UI] Debug Toggle: {self.state.show_debug}")
        
        # Camera and mouse inputs
        if w > 0 and h > 0:
            self.state.camera.update_aspect(w, h)
            
            if not io.want_capture_mouse:
                self._process_mouse_camera(io, w, h)
                self._process_mouse_selection(io, w, h, world_size)
    
    def _process_keyboard(self, io, dt: float):
        """Procesa inputs de teclado: Tab (boost/pause), Space (reset)."""
        t_now = time.time()
        
        # 1. Reset a Velocidad Óptima [Espacio]
        if imgui.is_key_pressed(imgui.Key.space):
            self.state.time_scale = 1.0
            self.state.paused = False
            self.state.boost_active = False
            self.state.add_log("SISTEMA: Velocidad restablecida a 1.0x.")

        # 2. Lógica de Tab (Doble-Tap vs Hold)
        tab_just_pressed = imgui.is_key_pressed(imgui.Key.tab)
        tab_held = imgui.is_key_down(imgui.Key.tab)
        
        if tab_just_pressed:
            # Detectar Doble-Tap (dentro de 0.3s)
            if (t_now - self.last_tab_time) < 0.3 and not self.state.boost_active:
                self.state.paused = not self.state.paused
                self.state.time_scale = 0.0 if self.state.paused else 1.0
                self.state.boost_active = False
                self.state.add_log(f"SISTEMA: {'Pausado' if self.state.paused else 'Reanudado'}")
                self.last_tab_time = 0  # Evitar triple-tap
            else:
                self.last_tab_time = t_now
        
        # 3. Acelerar mientras se mantiene Tab (Solo si NO está pausado)
        if tab_held and not self.state.paused:
            if not self.state.boost_active:
                self.state.boost_active = True
                self.state.add_log("BOOST: Acelerando evolución...")
            
            accel_rate = 8.0 * dt
            self.state.time_scale = min(UIConfig.BOOST_SPEED, self.state.time_scale + accel_rate)
        
        # 4. Al soltar Tab: Mantener velocidad
        elif self.state.boost_active and not tab_held:
            self.state.boost_active = False
            self.state.add_log(f"SISTEMA: Velocidad fijada en {self.state.time_scale:.1f}x")
    
    def _process_mouse_camera(self, io, w: int, h: int):
        """Procesa inputs de mouse para la cámara: zoom y pan."""
        # Pan con middle click
        if imgui.is_mouse_dragging(imgui.MouseButton_.middle):
            delta = io.mouse_delta
            vis_w, vis_h = self.state.camera.get_visible_area()
            move_x = -delta.x * (vis_w / w)
            move_y = -delta.y * (vis_h / h)
            self.state.camera.move(move_x, move_y)
        
        # Zoom con rueda
        wheel = io.mouse_wheel
        if wheel != 0:
            zoom_factor = 1.15 if wheel > 0 else 0.85
            self.state.camera.update_zoom(zoom_factor)
    
    def _process_mouse_selection(self, io, w: int, h: int, world_size: float):
        """Procesa clicks para selección de átomos y ondas de choque."""
        if not imgui.is_mouse_clicked(imgui.MouseButton_.left):
            return
            
        mx, my = io.mouse_pos.x, io.mouse_pos.y
        world_x, world_y = self.state.camera.screen_to_world(mx, my, w, h)
        
        # ONDA DE CHOQUE: Solo con CTRL
        if io.key_ctrl:
            apply_pulse = self.sim_data.get('apply_force_pulse')
            if apply_pulse:
                apply_pulse(world_x, world_y, 2.5)
                print(f"[PWR] Pulso de Fuerzas (CTRL+Click) en Mundo: [{world_x:.1f}, {world_y:.1f}]")
            return
        
        # SELECCIÓN DE ÁTOMOS
        pos_array = self.sim_data['pos'].to_numpy()
        is_active_array = self.sim_data['is_active'].to_numpy()
        
        # Buscar el más cercano
        dists_sq = np.sum((pos_array - np.array([world_x, world_y]))**2, axis=1)
        dists_sq[~is_active_array.astype(bool)] = 1e12
        
        idx = np.argmin(dists_sq)
        
        # Radio interactivo dinámico (Escalado por Zoom)
        vis_h = world_size / self.state.camera.zoom
        world_px = vis_h / h
        detect_rad = 25.0 * world_px
        
        if dists_sq[idx] < detect_rad**2:
            # Ciclo: Átomo -> Molécula -> Deselección
            if self.state.selected_idx == idx:
                if not self.state.selected_mol:
                    self.state.selected_mol = self.state.get_molecule_indices(idx)
                    print(f"[PICK] Molécula detectada: {len(self.state.selected_mol)} átomos.")
                else:
                    self.state.selected_idx = -1
                    self.state.selected_mol = []
            else:
                self.state.selected_idx = idx
                self.state.selected_mol = []
                print(f"[PICK] Átomo detectado: {idx}")
        else:
            # Click en vacío: Deseleccionar
            self.state.selected_idx = -1
            self.state.selected_mol = []
