"""
FrameLoop - Bucle Principal de Frame Modular
=============================================
Extrae la lógica del update() de main.py para mejor modularización.
Preserva todas las optimizaciones de rendimiento del Ultra-Loop V3.
"""

import time
import numpy as np
import taichi as ti

from src.core.perf_logger import get_perf_logger
from src.config import UIConfig
from src.systems.taichi_fields import total_bonds_broken_dist
from src.systems.molecule_detector import get_molecule_detector

# Submódulos extraídos
from src.core.molecule_scanner import scan_visible_known_molecules
from src.core.lod_bubbles import scan_macroscopic_bubbles


class FrameLoop:
    """
    Orquesta el loop de frame principal.
    
    Preserva las optimizaciones clave:
    - Single sync point (un solo to_numpy())
    - GPU buffer universal
    - Compute culling
    """
    
    def __init__(self, state, gpu_resources, render_resources):
        """
        Args:
            state: AppContext singleton
            gpu_resources: Dict con campos GPU y funciones
            render_resources: Dict con offsets y buffers
        """
        self.state = state
        self.gpu = gpu_resources
        self.render = render_resources
        self.perf = get_perf_logger()
        
        # Cache para LOD (Macroscopic bubbles)
        self._lod_cache = None
        self._lod_last_frame = -999
        self._lod_skip_count = 0

        # Host Buffers para Optimizacion V4 (Slice Sync)
        # OPTIMIZATION: NDArrays pequeños = transferencia más rápida
        # El viewport típicamente muestra 50-2500 partículas, usamos 3000 como cap.
        MAX_VIS = 3000  # Límite de partículas visibles (evita transferir 10k)
        MAX_BOND_VIS = 8000  # ~4 enlaces por partícula visible promedio
        
        self.host_stats = ti.ndarray(shape=(16), dtype=ti.f32)
        self.host_particles = ti.ndarray(shape=(MAX_VIS, 12), dtype=ti.f32)
        self.host_bonds = ti.ndarray(shape=(MAX_BOND_VIS, 2), dtype=ti.f32)
        self.host_highlights = ti.ndarray(shape=(256, 6), dtype=ti.f32)  # Reducido de 1024
        self.host_debug = ti.ndarray(shape=(32, 2), dtype=ti.f32)
        
    def tick(self, io, world_size, override_res=None):
        """
        Ejecuta un frame completo.
        
        Args:
            io: imgui IO object
            world_size: Tamaño del mundo
            override_res: (w, h) tuple for physical resolution (optional)
            
        Returns:
            Tuple de datos para rendering
        """
        self.perf.start("total")
        
        # 0. Sync inicial - ELIMINADO para async GPU
        # (Los syncs se hacen implícitamente en to_numpy() cuando necesitamos datos)
        
        if override_res:
            w, h = override_res
        else:
            w, h = int(io.display_size.x), int(io.display_size.y)
        
        # 1. Input handling (delegado al input_handler externo)
        
        # 2. FPS calculation
        now = time.time()
        dt_f = now - self.state.last_time
        if dt_f > 0:
            self.state.fps = 0.9 * self.state.fps + 0.1 * (1.0 / dt_f)
        self.state.last_time = now
        
        # 3. Culling bounds
        margin_culling = 200.0
        b = self.state.camera.get_culling_bounds(margin_culling)
        self.gpu['sim_bounds'][0] = float(b[0])
        self.gpu['sim_bounds'][1] = float(b[1])
        self.gpu['sim_bounds'][2] = float(b[2])
        self.gpu['sim_bounds'][3] = float(b[3])
        
        # 4. Simulation step (if not paused)
        if not self.state.paused:
            steps = int(self.state.time_scale)
            if np.random.random() < (self.state.time_scale - steps):
                steps += 1
                
            if steps > 0:
                if self.state.selected_idx >= 0 and self.state.selected_mol:
                    self.state.selected_mol = self.state.get_molecule_indices(self.state.selected_idx)
                
                self.perf.start("physics")
                self.gpu['run_simulation_fast'](steps)
                # Sync solo cuando necesitamos medir tiempo o hay selección activa
                # En modo normal, dejamos que la GPU corra libre (async)
                if self.state.selected_idx >= 0 or self.state.timeline.frame % 60 == 0:
                    ti.sync()
                self.perf.stop("physics")
        
        # 5. Pre-render GPU kernels
        zoom, cx, cy = self.state.camera.get_render_params()
        aspect = self.state.camera.aspect_ratio
        vis_h_half = world_size / (2.0 * zoom)
        vis_w_half = vis_h_half * aspect
        
        # 5. Pre-render Logic (Simplified LOD: Labels Only)
        # Ya no usamos burbujas gráficas. Solo etiquetas flotantes de moléculas al alejarse.
        # lod_threshold determina cuándo aparecen las etiquetas de fórmulas
        show_molecule_labels = zoom < self.state.lod_threshold
        
        # Átomos siempre visibles al 100%
        atoms_active = True
        alpha_micro = 1.0
        alpha_macro = 1.0 if show_molecule_labels else 0.0
        lod_active = show_molecule_labels  # Para generar datos de etiquetas
        
        lod_bubbles = None
        
        if atoms_active:
            # NORMAL MODE: Atom Rendering
            self.perf.start("grid")
            self.gpu['update_borders_gl'](zoom, cx, cy, aspect)
            self.gpu['prepare_bond_lines_gl'](zoom, cx, cy, aspect, self.host_bonds)
            # Pasamos ndarrays como buffers de salida
            self.gpu['compact_render_data'](self.host_stats, self.host_particles)
            # Sync debug info manually if needed or via ndarray too
            self.perf.stop("grid")
            
            if self.state.selected_idx >= 0:
                if self.state.selected_mol:
                    self.gpu['prepare_highlights'](self.state.selected_idx, 1, self.host_highlights)
                else:
                    self.gpu['prepare_highlights'](self.state.selected_idx, 0, self.host_highlights)
        
        # 6. Data transfer (ULTRA SYNC V4 - Single Point of Truth)
        synced = self._sync_gpu_all()
        stats_np = synced['stats']
        
        # Extract stats from host ndarray
        n_vis = int(stats_np[0])
        n_bonds = int(stats_np[1])
        n_h = int(stats_np[2])
        n_sim = int(stats_np[3])
        tot_bonds = int(stats_np[4])
        tot_muts = int(stats_np[5])
        tot_tunnels = int(stats_np[6])
        act_part = int(stats_np[7])
        
        # n_vis es 0 si no hay átomos en absoluto (Micro factor = 0)
        if not atoms_active:
            n_vis = 0
            
        # Camera HUD/UI projection parameters
        self._cam_params_label = (cx, cy, vis_w_half, vis_h_half)
        
        # Update state counters
        self._update_counters(tot_bonds, tot_muts, tot_tunnels)
        self.state.n_simulated_val = n_sim
        self.state.n_visible_val = n_vis
        
        self.perf.set_counter("n_visible", n_vis)
        self.perf.set_counter("simulated_count", n_sim)
        self.perf.set_counter("bonds_count", tot_bonds)
        self.perf.set_counter("active_particles_count", act_part)
        
        # 7. Extract render data
        if atoms_active:
             render_data = self._extract_render_data_v4(synced, n_vis, n_bonds, n_h)
        else:
             render_data = {}
             
        if lod_active:
             # OPTIMIZATION: Usa el mismo sync 'master' o 'pos'
             self._lod_skip_count += 1
             if self._lod_skip_count >= 10 or self._lod_cache is None:
                 self._lod_skip_count = 0
                 self.perf.start("logic_py")
                 self._lod_cache = scan_macroscopic_bubbles(self.state, self.gpu, synced)
                 self.perf.stop("logic_py")
             
             lod_bubbles = self._lod_cache
             
        self.perf.stop("data_transfer")
        
        # 8. Process highlights
        self.perf.start("cpu_logic")
        highlight_data = self._process_highlights(n_h, render_data.get('h_pos_data'), synced)
        
        # 9. Molecular Detection (ASYNC V5)
        # Ejecutar en hilo separado para no bloquear render
        is_early = self.state.timeline.frame < 10
        should_detect = not self.state.paused and (is_early or self.state.timeline.frame % 300 == 0)
        
        from src.systems.async_chemistry import get_async_chemistry_worker
        async_chem = get_async_chemistry_worker()
        
        # Encolar job si toca detectar y hay datos
        if should_detect and synced.get('atom_types') is not None:
            n_part = self.state.n_particles_val
            
            # Calcular ROI (Lazy Evaluation)
            # Damos un margen del 20% extra fuera de cámara
            cam = self.state.camera
            vis_w, vis_h = cam.get_visible_area()
            roi = (
                cam.x - vis_w * 0.6,
                cam.y - vis_h * 0.6,
                cam.x + vis_w * 0.6,
                cam.y + vis_h * 0.6
            )
            
            # Si el zoom es muy alejado, procesar todo (Sin ROI)
            if vis_w > self.state.world_size * 0.9:
                roi = None
            
            async_chem.submit_job(
                synced['atom_types'],
                synced['molecule_id'],
                synced['num_enlaces'],
                synced['pos'],
                n_part,
                roi=roi
            )
        
        # Recoger resultados (siempre, non-blocking)
        chem_result = async_chem.get_result()
        if chem_result:
            # Actualizar stats si hay resultado
            self.perf.set_counter("chem_async_ms", chem_result.get('process_time_ms', 0))

            
        self.perf.stop("cpu_logic")
        
        # Pack all data for rendering
        frame_data = {
            'w': w, 'h': h,
            'camera_params': (cx, cy, vis_w_half, vis_h_half),
            'pos_vis': render_data.get('pos_vis'),
            'col_vis': render_data.get('col_vis'),
            'scale_vis': render_data.get('scale_vis'),  # 2.5D depth scale
            'type_vis': render_data.get('type_vis'),    # Synced atom types
            'bonds_gl': render_data.get('bonds_gl'),
            'debug_gl': render_data.get('debug_gl'),
            'highlight_lines': highlight_data['lines'],
            'rings_sel': highlight_data['rings_sel'],
            'rings_nei': highlight_data['rings_nei'],
            'rings_known': (highlight_data.get('rings_known', np.array([])), highlight_data.get('rings_known_col', np.array([]))),  # Known molecules glow as tuple (pos, col)
            'n_vis': n_vis,  # Para atom labels
            'lod_active': lod_active,
            'lod_bubbles': lod_bubbles,
            'factor_micro': alpha_micro, # Corrected: match new variable names
            'factor_macro': alpha_macro,
            'zones': self.state.progression.zones.zones if hasattr(self.state.progression, 'zones') else []
        }

        
        # Almacenar en state.render_data para UI (atom labels, etc.)
        frame_data['synced'] = synced # Exponer datos sincronizados de este frame
        self.state.render_data = frame_data
        
        return frame_data
    
    def render_frame(self, frame_data, world_size, bonds_only=False):
        """
        Renderiza el frame con los datos preparados.
        """
        self.perf.start("render")
        
        w, h = frame_data['w'], frame_data['h']
        camera_params = frame_data['camera_params']
        
        # 0. Limpiar pantalla una vez por frame antes de dibujar capas
        self.state.renderer.clear_screen(w, h)
        
        cx, cy, vis_w_half, vis_h_half = camera_params
        
        # 1. Renderizar Zonas Especiales (Como fondo)
        if 'zones' in frame_data:
            self.state.renderer.render_zones(frame_data['zones'], camera_params, w, h)
        
        # Para etiquetas de moléculas (sin burbujas gráficas)
        f_macro = frame_data.get('factor_macro', 0.0)
        self.state.lod_factor_macro = f_macro
        self.state.show_molecule_labels = f_macro > 0.5  # Flag para UI
        
        # Solo renderizamos átomos y enlaces (siempre visibles)
        self.state.renderer.render(
            frame_data['pos_vis'],
            frame_data['col_vis'],
            frame_data.get('scale_vis'),
            frame_data.get('bonds_gl'),
            frame_data.get('debug_gl'),
            frame_data.get('highlight_lines'),
            w, h,
            camera_params=camera_params,
            bonds_only=bonds_only,
            alpha=1.0  # Siempre 100% opacidad
        )
        
        # Anillos de selección (siempre visibles)
        r_world_sel = UIConfig.HIGHLIGHT_RADIUS * vis_w_half
        if len(frame_data['rings_sel']) > 0:
            self.state.renderer.render_rings(
                frame_data['rings_sel'], r_world_sel, 
                UIConfig.COLOR_PRIMARY, camera_params, h, alpha=1.0
            )
        if len(frame_data['rings_nei']) > 0:
            self.state.renderer.render_rings(
                frame_data['rings_nei'], r_world_sel,
                UIConfig.COLOR_CYAN_NEON, camera_params, h, alpha=1.0
            )
        
        # Glow de Quimidex (Muestra las moléculas ya descubiertas)
        rings_known_data = frame_data.get('rings_known')
        if isinstance(rings_known_data, tuple) and len(rings_known_data[0]) > 0:
             k_pos, k_col = rings_known_data
             self.state.renderer.render_rings_colored(
                 k_pos, k_col, r_world_sel * 1.1, camera_params, h, alpha=1.0
             )

        
        self.state.renderer.ctx.viewport = (0, 0, w, h)
        self.perf.stop("render")
        
        # Finalizar frame
        self.perf.stop("total")
        self.perf.end_frame(self.state.fps)
        
        # Periodic profiling output (cada 120 frames = ~2 segundos)
        if self.perf.frame_count % 120 == 0 and self.perf.frame_count > 0:
            fc = self.perf.frame_count
            t = self.perf._totals
            # Calculate averages for last period
            print(f"[PERF] Frames: {fc}, FPS Avg: {t['fps']/fc:.1f}"
                  f" | Phy: {t['physics_ms']/fc:.2f}ms"
                  f" | Grid: {t['grid_ms']/fc:.2f}ms"
                  f" | Data: {t['data_transfer_ms']/fc:.2f}ms"
                  f" | Logic: {t['cpu_logic_ms']/fc:.2f}ms"
                  f" | Render: {t['render_ms']/fc:.2f}ms"
                  f" | Chem: {t['chemistry_ms']/fc:.2f}ms")
    
    def _update_counters(self, tot_bonds, tot_muts, tot_tunnels):
        """Actualiza contadores y genera logs de eventos."""
        # Enlaces
        if tot_bonds > getattr(self.state, 'last_bonds', 0):
            diff = tot_bonds - self.state.last_bonds
            self.state.stats["bonds_formed"] += diff
            # self.state.add_log(f"ENLACE: +{diff} uniones químicas.")
        elif tot_bonds < getattr(self.state, 'last_bonds', 0):
            diff = self.state.last_bonds - tot_bonds
            self.state.stats["bonds_broken"] += diff
            # self.state.add_log(f"ROTURA: {diff} enlaces disueltos.")
        
        # Mutaciones
        if tot_muts > getattr(self.state, 'last_mutations', 0):
            diff = tot_muts - self.state.last_mutations
            self.state.stats["mutations"] += diff
            # self.state.add_log(f"CATÁLISIS: {diff} átomos activos.")
        
        # Túneles
        if tot_tunnels > getattr(self.state, 'last_tunnels', 0):
            diff = tot_tunnels - self.state.last_tunnels
            self.state.stats["tunnels"] += diff
            # self.state.add_log(f"TRANSICIÓN: {diff} saltos de energía.")
        
        self.state.last_bonds = tot_bonds
        self.state.last_mutations = tot_muts
        self.state.last_tunnels = tot_tunnels
    
    def _extract_render_data_v4(self, synced, n_vis, n_bonds, n_h):
        """Extrae datos de render usando el nuevo sistema V4 NDArray."""
        data = {}
        
        if n_vis > 0:
            data_vis = synced['particles_vis']
            
            # Z-Sorting: ordenar por scale (depth) - lejanos primero
            scale_col = data_vis[:, 5]
            sort_idx = np.argsort(scale_col)
            data_sorted = data_vis[sort_idx]
            
            data['pos_vis'] = np.ascontiguousarray(data_sorted[:, 0:2])
            data['col_vis'] = np.ascontiguousarray(data_sorted[:, 2:5])
            data['scale_vis'] = np.ascontiguousarray(data_sorted[:, 5:6])
            data['type_vis'] = np.ascontiguousarray(data_sorted[:, 6:7])
        
        if n_bonds > 0:
            data['bonds_gl'] = synced['bonds_vis'].astype(np.float32)
        
        if n_h > 0:
             # Fallback momentáneo si highlights no están aún en synced
             pass
        
        if self.state.show_debug:
             # data['debug_gl'] = ...
             pass
        
        return data
    
    def _sync_gpu_all(self):
        """Sincronización inteligente para minimizar latencias (V4 NDArray)."""
        self.perf.start("data_transfer")
        
        # 1. Stats (Always sync 16 floats, extremely fast)
        stats_np = self.host_stats.to_numpy()
        n_vis = int(stats_np[0])
        n_bonds = int(stats_np[1])
        
        # 2. Slice Sync (Solo traemos lo usado)
        particles_vis_np = self.host_particles.to_numpy()[0:n_vis]
        bonds_vis_np = self.host_bonds.to_numpy()[0:n_bonds]
        
        # 3. Otros campos: Solo si hay detección química o selección activa
        is_early = self.state.timeline.frame < 10
        should_detect = not self.state.paused and (is_early or self.state.timeline.frame % 600 == 0)
        show_mols = getattr(self.state, 'show_molecules', False)
        should_bubble = self.state.camera.zoom < self.state.lod_threshold and (self._lod_skip_count >= 10 or self._lod_cache is None)
        
        pos_np = None
        types_np = None
        num_enl_np = None
        mol_id_np = None
        active_np = None
        enlaces_np = None
        
        # Datos estructurales (Sincronización masiva pero INFRECUENTE)
        if should_detect or should_bubble or self.state.selected_idx >= 0:
            # show_mols ya no requiere sync completo gracias a V4 Scanner
            pos_np = self.gpu['pos'].to_numpy()
            active_np = self.gpu['is_active'].to_numpy()
            
            if should_detect or self.state.selected_idx >= 0 or show_mols:
                types_np = self.gpu['atom_types'].to_numpy()
                num_enl_np = self.gpu['num_enlaces'].to_numpy()
                mol_id_np = self.gpu['molecule_id'].to_numpy()
                
                if self.state.selected_idx >= 0:
                    enlaces_np = self.gpu['enlaces_idx'].to_numpy()
            
        self.perf.stop("data_transfer")
        
        return {
            'stats': stats_np,
            'particles_vis': particles_vis_np,
            'bonds_vis': bonds_vis_np,
            'pos': pos_np,
            'atom_types': types_np,
            'num_enlaces': num_enl_np,
            'molecule_id': mol_id_np,
            'is_active': active_np,
            'enlaces_idx': enlaces_np
        }

    def _process_highlights(self, n_h, h_pos_data, synced):
        """Highlight con datos ya sincronizados."""
        highlight_lines = []
        ring_centers_selected = []
        ring_centers_neighbors = []
        
        zoom, cx, cy = self.state.camera.get_render_params()
        vis_h = 15000.0 / zoom
        atom_radius_vis = 0.006 * vis_h
        
        if self.state.selected_idx >= 0 and self.state.selected_mol:
            pos_np = synced['pos'] if synced['pos'] is not None else self.gpu['pos'].to_numpy() # Fix truthiness
            mol_indices = self.state.selected_mol
            
            p_sel = pos_np[self.state.selected_idx]
            ring_centers_selected.append([p_sel[0], p_sel[1]])
            
            for idx in mol_indices:
                if idx != self.state.selected_idx:
                    p = pos_np[idx]
                    ring_centers_neighbors.append([p[0], p[1]])
            
            enlaces_np = synced['enlaces_idx']
            num_enlaces_np = synced['num_enlaces']
            
            if enlaces_np is not None:
                mol_set = set(mol_indices)
                for idx in mol_indices:
                    p_i = pos_np[idx]
                    for k in range(int(num_enlaces_np[idx])):
                        j = int(enlaces_np[idx, k])
                        if j > idx and j in mol_set:
                            p_j = pos_np[j]
                            dx, dy = p_j[0] - p_i[0], p_j[1] - p_i[1]
                            dist = np.sqrt(dx*dx + dy*dy)
                            if dist > 0.001:
                                nx, ny = dx/dist, dy/dist
                                highlight_lines.extend([
                                    p_i[0] + nx * atom_radius_vis, p_i[1] + ny * atom_radius_vis,
                                    p_j[0] - nx * atom_radius_vis, p_j[1] - ny * atom_radius_vis
                                ])
        
        # Known molecules glow
        if getattr(self.state, 'show_molecules', False):
            rings_known, rings_known_col = scan_visible_known_molecules(self.state, self.gpu, synced)
        else:
            rings_known = np.array([], dtype=np.float32)
            rings_known_col = np.array([], dtype=np.float32)
        
        return {
            'lines': np.array(highlight_lines, dtype=np.float32) if highlight_lines else None,
            'rings_sel': np.array(ring_centers_selected, dtype=np.float32) if ring_centers_selected else np.array([]),
            'rings_nei': np.array(ring_centers_neighbors, dtype=np.float32) if len(ring_centers_neighbors) > 0 else np.array([]),
            'rings_known': rings_known,
            'rings_known_col': rings_known_col,
        }
