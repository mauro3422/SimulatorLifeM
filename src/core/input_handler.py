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
        
        # WASD siempre activo (movimiento del jugador)
        self._process_player_movement(dt)
        
        # Actualizar sistema de misiones y metabolismo
        if not self.state.paused:
            self.state.progression.update(dt)
            self.state.atp = self.state.progression.atp
        
        # Keyboard inputs (otros, solo si ImGui no captura)
        if not io.want_capture_keyboard:
            self._process_keyboard(io, dt)
        
        # F3 Debug toggle (always available)
        if imgui.is_key_pressed(imgui.Key.f3):
            self.state.show_debug = not self.state.show_debug
            print(f"[UI] Debug Toggle: {self.state.show_debug}")
        
        # M Molecule highlight toggle (always available)
        if imgui.is_key_pressed(imgui.Key.m):
            self.state.show_molecules = not getattr(self.state, 'show_molecules', False)
            status = "ACTIVADO" if self.state.show_molecules else "DESACTIVADO"
            print(f"[UI] Highlight Moléculas (M): {status}")
        
        # Camera and mouse inputs
        if w > 0 and h > 0:
            self.state.camera.update_aspect(w, h)
            
            if not io.want_capture_mouse:
                self._process_mouse_camera(io, w, h)
                self._process_mouse_selection(io, w, h, world_size)
    
    def _process_keyboard(self, io, dt: float):
        """Procesa inputs de teclado: Tab (boost/pause), Space (reset)."""
        t_now = time.time()
        
        # 1. Centrar cámara en jugador [Espacio]
        if imgui.is_key_pressed(imgui.Key.space):
            # Centrar cámara en el jugador
            pos = self.sim_data.get('pos')
            if pos is not None:
                player_pos = pos.to_numpy()[self.state.player_idx]
                self.state.camera.x = player_pos[0]
                self.state.camera.y = player_pos[1]
                self.state.camera.set_zoom(15.0)  # Zoom cercano para ver al jugador
            self.state.time_scale = 0.3  # Tiempo lento
            self.state.paused = False
            self.state.boost_active = False
            
            # SELECCIÓN: Mostrar al jugador en el inspector
            self.state.selected_idx = self.state.player_idx
            self.state.selected_mol = self.state.get_molecule_indices(self.state.player_idx)
            
            mol_status = "ÁTOMO LIBRE" if len(self.state.selected_mol) <= 1 else f"MOLÉCULA ({len(self.state.selected_mol)} átomos)"
            self.state.add_log(f"JUGADOR: Cámara centrada. Eres: {mol_status}")
            
        # 2. Toggle Etiquetas [L]
        if imgui.is_key_pressed(imgui.Key.l):
            self.state.show_labels = not self.state.show_labels
            status = "VISIBLES" if self.state.show_labels else "OCULTAS"
            self.state.add_log(f"UI: Etiquetas de átomos {status}")

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

        # 5. Soltar Enlaces [X]
        if imgui.is_key_pressed(imgui.Key.x):
            self._drop_player_bonds()

        # 6. Cambiar Foco de Consciencia (Q-Anterior, E-Siguiente)
        if imgui.is_key_pressed(imgui.Key.q) or imgui.is_key_pressed(imgui.Key.e):
            self._cycle_consciousness(forward=imgui.is_key_pressed(imgui.Key.e))
    
    def _cycle_consciousness(self, forward=True):
        """Cicla la consciencia del jugador entre los átomos de su propia molécula."""
        molecule = self.state.get_molecule_indices(self.state.player_idx)
        if len(molecule) <= 1:
            return
            
        current_idx = self.state.player_idx
        try:
            pos_in_mol = molecule.index(current_idx)
            next_pos = (pos_in_mol + (1 if forward else -1)) % len(molecule)
            self._transfer_consciousness(molecule[next_pos])
        except ValueError:
            pass
    
    def _drop_player_bonds(self):
        """Suelta todos los enlaces del átomo del jugador."""
        player_idx = self.state.player_idx
        enlaces = self.sim_data.get('enlaces_idx')
        num_enl = self.sim_data.get('num_enlaces')
        manos = self.sim_data.get('manos_libres')
        
        if any(v is None for v in [enlaces, num_enl, manos]):
            return
            
        enlaces_np = enlaces.to_numpy()
        num_enl_np = num_enl.to_numpy()
        manos_np = manos.to_numpy()
        
        count = num_enl_np[player_idx]
        if count == 0:
            return
            
        # Para cada átomo enlazado, eliminar la referencia al jugador
        for i in range(count):
            target_idx = enlaces_np[player_idx, i]
            if target_idx == -1: continue
            
            # Buscar al jugador en los enlaces del target
            target_count = num_enl_np[target_idx]
            target_links = enlaces_np[target_idx]
            
            new_links = []
            for j in range(target_count):
                link = target_links[j]
                if link != player_idx:
                    new_links.append(link)
            
            # Actualizar target
            num_enl_np[target_idx] = len(new_links)
            manos_np[target_idx] += 1.0 # Recuperar mano
            
            # Limpiar array de enlaces del target
            enlaces_np[target_idx].fill(-1)
            for j, link in enumerate(new_links):
                enlaces_np[target_idx, j] = link

        # Limpiar enlaces del jugador
        enlaces_np[player_idx].fill(-1)
        num_enl_np[player_idx] = 0
        manos_np[player_idx] = float(self.state.get_valence(player_idx)) if hasattr(self.state, 'get_valence') else 4.0
        
        # Subir a GPU
        enlaces.from_numpy(enlaces_np)
        num_enl.from_numpy(num_enl_np)
        manos.from_numpy(manos_np)
        
        self.state.add_log("🧬 Molécula desensamblada manualmente.")
        self.state.progression.check_mission()
        print(f"[INPUT] Player {player_idx} dropped all bonds.")
    
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
        """Procesa clicks para selección de átomos, saltos de consciencia y ondas de choque."""
        is_left_clicked = imgui.is_mouse_clicked(imgui.MouseButton_.left)
        is_right_clicked = imgui.is_mouse_clicked(imgui.MouseButton_.right)
        
        if not (is_left_clicked or is_right_clicked):
            return
            
        mx, my = io.mouse_pos.x, io.mouse_pos.y
        world_x, world_y = self.state.camera.screen_to_world(mx, my, w, h)
        
        # ONDA DE CHOQUE: Solo con CTRL + Click Izquierdo
        if io.key_ctrl and is_left_clicked:
            apply_pulse = self.sim_data.get('apply_force_pulse')
            if apply_pulse:
                apply_pulse(world_x, world_y, 2.5)
                print(f"[PWR] Pulso de Fuerzas (CTRL+Click) en Mundo: [{world_x:.1f}, {world_y:.1f}]")
            return
        
        # SELECCIÓN Y ATRACCIÓN DE ÁTOMOS
        pos_array = self.sim_data['pos'].to_numpy()
        is_active_array = self.sim_data['is_active'].to_numpy()
        player_idx = self.state.player_idx
        
        # Buscar el átomo más cercano al click
        dists_sq = np.sum((pos_array - np.array([world_x, world_y]))**2, axis=1)
        dists_sq[~is_active_array.astype(bool)] = 1e12
        dists_sq[player_idx] = 1e12  # Excluir al jugador
        
        idx = np.argmin(dists_sq)
        
        # Radio interactivo dinámico (Escalado por Zoom)
        vis_h = world_size / self.state.camera.zoom
        world_px = vis_h / h
        detect_rad = 50.0 * world_px
        
        if dists_sq[idx] < detect_rad**2:
            # 0. DOBLE CLICK: Centrar, Inspeccionar y Tiempo Bala
            if imgui.is_mouse_double_clicked(imgui.MouseButton_.left):
                # Centrar cámara
                target_pos = pos_array[idx]
                self.state.camera.x = target_pos[0]
                self.state.camera.y = target_pos[1]
                self.state.camera.set_zoom(15.0)
                
                # Configurar simulación
                self.state.time_scale = 0.3
                self.state.paused = False
                
                # Seleccionar Molécula completa
                self.state.selected_idx = idx
                self.state.selected_mol = self.state.get_molecule_indices(idx)
                
                mol_status = "ÁTOMO LIBRE" if len(self.state.selected_mol) <= 1 else f"MOLÉCULA ({len(self.state.selected_mol)} átomos)"
                self.state.add_log(f"🔎 Inspeccionando: {mol_status}")
                return

            # 1. CLICK DERECHO: Saltar consciencia al átomo (Cambiar de cuerpo)
            if is_right_clicked:
                self._jump_consciousness_to(idx)
                return

            # 2. CLICK IZQUIERDO: Atraer/Enlazar o Seleccionar
            if is_left_clicked:
                player_pos = pos_array[player_idx]
                dist_to_player = np.sqrt(np.sum((pos_array[idx] - player_pos)**2))
                ATTRACT_RANGE = 500.0
                
                if dist_to_player <= ATTRACT_RANGE:
                    # DENTRO DEL RANGO: Atraer + Enlazar
                    if dist_to_player > 50.0:
                        vel_array = self.sim_data['vel'].to_numpy()
                        direction = player_pos - pos_array[idx]
                        dist = np.linalg.norm(direction)
                        if dist > 1:
                            direction = direction / dist
                            ATTRACT_SPEED = 250.0
                            vel_array[idx] = direction * ATTRACT_SPEED
                            self.sim_data['vel'].from_numpy(vel_array)
                    
                    self._force_bond_with(idx)
                    self.state.selected_idx = idx
                    self.state.selected_mol = []
                else:
                    # FUERA DEL RANGO: Modo selección/inspección
                    if self.state.selected_idx == idx:
                        if not self.state.selected_mol:
                            self.state.selected_mol = self.state.get_molecule_indices(idx)
                        else:
                            self.state.selected_idx = -1
                            self.state.selected_mol = []
                    else:
                        self.state.selected_idx = idx
                        self.state.selected_mol = []
                        self.state.add_log(f"👁️ Inspeccionando átomo remoto")
        else:
            # Click en vacío: Deseleccionar
            if is_left_clicked:
                self.state.selected_idx = -1
                self.state.selected_mol = []
    
    def _transfer_consciousness(self, target_idx: int):
        """Transfiere la consciencia del jugador a un nuevo átomo (Salto de cuerpo)."""
        import src.config as cfg
        types_np = self.sim_data['atom_types'].to_numpy()
        name_t = cfg.TIPOS_NOMBRES[types_np[target_idx]]
        
        # 1. Cambiar ID del Jugador (AppState y Taichi)
        self.state.player_idx = target_idx
        from src.systems.taichi_fields import player_idx as ti_player_idx
        ti_player_idx[None] = target_idx
        
        # 2. Feedback visual y log
        self.state.add_log(f"✨ CONSCIENCIA: Ahora eres {name_t}")
        print(f"[INPUT] Consciousness Transfer to {target_idx}")
        
        # 3. Actualizar Selección e Inspector
        self.state.selected_idx = target_idx
        self.state.selected_mol = self.state.get_molecule_indices(target_idx)
        
        # 4. Verificar misiones inmediatamente
        self.state.progression.check_mission()

    def _jump_consciousness_to(self, target_idx: int):
        """Legacy wrapper para salto por click."""
        self._transfer_consciousness(target_idx)
    
    def _force_bond_with(self, target_idx: int) -> bool:
        """Fuerza un enlace entre el jugador y el átomo objetivo si es químicamente válido.
        Retorna True si el enlace fue exitoso.
        """
        player_idx = self.state.player_idx
        
        # Obtener campos necesarios
        enlaces = self.sim_data.get('enlaces_idx')
        num_enl = self.sim_data.get('num_enlaces')
        manos = self.sim_data.get('manos_libres')
        atom_types = self.sim_data.get('atom_types')
        
        if any(v is None for v in [enlaces, num_enl, manos, atom_types]):
            print("[BOND] Campos no disponibles")
            return False
        
        # Leer datos
        enlaces_np = enlaces.to_numpy()
        num_enl_np = num_enl.to_numpy()
        manos_np = manos.to_numpy()
        types_np = atom_types.to_numpy()
        
        import src.config as cfg
        type_p = types_np[player_idx]
        type_t = types_np[target_idx]
        name_p = cfg.TIPOS_NOMBRES[type_p]
        name_t = cfg.TIPOS_NOMBRES[type_t]
        
        # 1. Verificar AFINIDAD (Sentido químico)
        # Obtenemos la afinidad desde la config
        atom_info_p = cfg.ATOMS.get(name_p, {})
        affid_dict_p = atom_info_p.get("affinities", {})
        afinidad = affid_dict_p.get(name_t, 0.0)
        
        if afinidad <= 0.01:
            self.state.add_log(f"⚠️ {name_p} y {name_t} no tienen afinidad")
            print(f"[BOND] Sin afinidad: {name_p} + {name_t}")
            return False

        # 2. Verificar valencia disponible
        if manos_np[player_idx] < 0.5:
            self.state.add_log("❌ No tenés manos libres")
            return False
        if manos_np[target_idx] < 0.5:
            self.state.add_log("❌ Átomo sin manos libres")
            return False
        
        # 3. Verificar si ya están enlazados
        for i in range(num_enl_np[player_idx]):
            if enlaces_np[player_idx, i] == target_idx:
                self.state.add_log("⚠️ Ya estás enlazado")
                return False
        
        # 4. Crear enlace
        slot_p = num_enl_np[player_idx]
        slot_t = num_enl_np[target_idx]
        
        if slot_p < 8 and slot_t < 8:  # MAX_BONDS = 8
            enlaces_np[player_idx, slot_p] = target_idx
            enlaces_np[target_idx, slot_t] = player_idx
            num_enl_np[player_idx] += 1
            num_enl_np[target_idx] += 1
            manos_np[player_idx] -= 1.0
            manos_np[target_idx] -= 1.0
            
            # Subir a GPU
            enlaces.from_numpy(enlaces_np)
            num_enl.from_numpy(num_enl_np)
            manos.from_numpy(manos_np)
            
            self.state.add_log(f"✅ ¡Enlace {name_p}-{name_t} formado!")
            print(f"[BOND] Enlace creado: {player_idx} <-> {target_idx}")
            
            # Verificar hito inmediatamente
            self.state.progression.check_mission()
            
            return True
        else:
            self.state.add_log("❌ Demasiados enlaces")
            return False
    
    def _process_player_movement(self, dt: float):
        """Procesa WASD para mover al átomo del jugador."""
        # Fuerza base del jugador (reducida para no romper enlaces)
        PLAYER_FORCE = 1500.0  # Reducido de 3000 para no romper enlaces
        
        fx, fy = 0.0, 0.0
        
        # WASD movement (Y invertido para coincidir con pantalla)
        if imgui.is_key_down(imgui.Key.w) or imgui.is_key_down(imgui.Key.up_arrow):
            fy -= PLAYER_FORCE  # Arriba = -Y en pantalla
        if imgui.is_key_down(imgui.Key.s) or imgui.is_key_down(imgui.Key.down_arrow):
            fy += PLAYER_FORCE  # Abajo = +Y en pantalla
        if imgui.is_key_down(imgui.Key.a) or imgui.is_key_down(imgui.Key.left_arrow):
            fx -= PLAYER_FORCE
        if imgui.is_key_down(imgui.Key.d) or imgui.is_key_down(imgui.Key.right_arrow):
            fx += PLAYER_FORCE
        
        # Consumir ATP si se está moviendo
        if fx != 0 or fy != 0:
            self.state.progression.consume_atp(self.state.progression.move_cost * dt)
        
        # Guardar la fuerza para aplicar en la física
        self.state.player_force = [fx, fy]
        
        # Aplicar fuerza a TODA la molécula del jugador (no solo al átomo)
        if (fx != 0 or fy != 0) and self.sim_data.get('vel') is not None:
            player_idx = self.state.player_idx
            vel = self.sim_data['vel']
            
            # Obtener todos los átomos de la molécula del jugador
            molecule_indices = self.state.get_molecule_indices(player_idx)
            if not molecule_indices:
                molecule_indices = [player_idx]
            
            # Leer velocidad actual
            current_vel = vel.to_numpy()
            
            # Aplicar fuerza a TODOS los átomos de la molécula
            for idx in molecule_indices:
                current_vel[idx, 0] += fx * dt
                current_vel[idx, 1] += fy * dt
                
                # Limitar velocidad
                MAX_PLAYER_SPEED = 200.0  # Aumentado ya que ahora la molécula se mueve junta
                speed = np.sqrt(current_vel[idx, 0]**2 + current_vel[idx, 1]**2)
                if speed > MAX_PLAYER_SPEED:
                    current_vel[idx] *= MAX_PLAYER_SPEED / speed
            
            # Subir a GPU
            vel.from_numpy(current_vel)

