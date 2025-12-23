"""
Progression Manager - Sistema de Metabolismo, Zonas y misiones
==============================================================
Gestiona el ATP, las misiones y los efectos de las zonas especiales.
"""

import time
import numpy as np
import src.config as cfg

class ProgressionManager:
    def __init__(self, context):
        self.ctx = context
        
        # --- Metabolismo (ATP) ---
        self.atp = 50.0        # ATP inicial
        self.max_atp = 100.0
        self.atp_decay = 0.5    # Pérdida pasiva por segundo
        self.move_cost = 2.0    # Costo por segundo de movimiento
        
        # --- Misiones Exploratorias ---
        self.missions = [
            {"id": "hh", "name": "Formar Hidrógeno (H2)", "formula": "H2", "reward": 30, "buff": "speed"},
            {"id": "h2o", "name": "Formar Agua (H2O)", "formula": "H2O1", "reward": 50, "buff": "stability"},
            {"id": "ch4", "name": "Formar Metano (CH4)", "formula": "CH4", "reward": 70, "buff": "valence"},
            {"id": "hcn", "name": "Formar Cianuro (HCN)", "formula": "C1H1N1", "reward": 80, "buff": "attraction"},
            {"id": "adenine", "name": "Formar Adenina (C5H5N5)", "formula": "C5H5N5", "reward": 200, "buff": "spark", "needs_clay": True},
        ]
        self.current_mission_idx = 0
        self.completed_missions = []
        self.active_buffs = set()
        
        # --- Zonas ---
        from src.systems.zone_manager import get_zone_manager
        self.zones = get_zone_manager(context.world_size if hasattr(context, 'world_size') else 15000.0)
        
        # Estado de zona actual
        self.current_zone_name = None
        self.in_clay = False
        self.in_vent = False
        
        self.last_update = time.time()
        
    def update(self, dt: float):
        """Actualiza el metabolismo y verifica misiones."""
        if self.ctx.paused:
            return
            
        # 1. Pasive Decay
        self.atp = max(0.0, self.atp - self.atp_decay * dt)
        
        # 2. Check Death (ATP = 0)
        if self.atp <= 0.0:
            self._handle_energy_death()
            
        # 3. Verificar posición para efectos de zona
        player_pos = self.ctx.get_player_pos()
        if player_pos is not None:
            self._check_zones(player_pos)
            
        # 4. Las misiones ahora se verifican por EVENTOS (bonding o analysis tick)
        # para evitar el uso de CPU verificando cada frame.

    def _check_zones(self, player_pos):
        """Aplica efectos físicos según la zona actual."""
        zone = self.zones.get_zone_at(player_pos)
        
        # Reset de estados
        self.in_clay = False
        self.in_vent = False
        
        if zone:
            if zone.name != self.current_zone_name:
                self.ctx.add_log(f"📍 ENTRANDO: {zone.name}", "zone_entry")
                self.current_zone_name = zone.name

            if zone.type.value == "Clay":
                self.in_clay = True
            elif zone.type.value == "Vent":
                self.in_vent = True
                # Las ventilas dan un poco de ATP (calor/energía) pero son inestables
                self.grant_atp(0.1) 
        else:
            if self.current_zone_name:
                self.ctx.add_log("📍 SALIENDO DE ZONA", "zone_exit")
                self.current_zone_name = None

    def _check_mission_progress(self):
        """Verifica misiones y calcula buffs activos basados en la molécula actual."""
        player_idx = self.ctx.player_idx
        sim = self.ctx.sim
        if not sim: return

        # BFS DIRECTO: No dependemos del Analyzer (que es lento/polling)
        # Obtenemos los datos actuales de la CPU (sincronizados desde InputHandler o GPU)
        from src.systems.molecular_analyzer import get_molecular_analyzer
        analyzer = get_molecular_analyzer()
        
        try:
            enl_np = sim['enlaces_idx'].to_numpy()
            num_np = sim['num_enlaces'].to_numpy()
            types_np = sim['atom_types'].to_numpy()
        except:
            return

        indices = analyzer.get_molecule_indices(player_idx, enl_np, num_np)
        
        if len(indices) < 2:
            # Re-calcular buffs aunque no haya molécula (para mantener los permanentes)
            self._update_all_buffs()
            return
            
        formula = analyzer.get_formula(indices, types_np)
        
        # DEBUG: Ver qué detectamos para el jugador
        if self.current_mission_idx < len(self.missions):
            mission = self.missions[self.current_mission_idx]
            # print(f"[DEBUG MISSION] Player Formula: {formula} | Target: {mission['formula']}")
        
        # 1. Verificar Misión Principal
        if self.current_mission_idx < len(self.missions):
            mission = self.missions[self.current_mission_idx]
            
            # Verificar requisitos de zona (ej: Adenina necesita arcilla)
            zone_req_met = True
            if mission.get("needs_clay", False) and not self.in_clay:
                zone_req_met = False
                
            if formula == mission["formula"] and zone_req_met:
                self._complete_mission(mission)
        
        # Siempre asegurar que los buffs están al día (por si acaso)
        self._update_all_buffs()

    def _update_all_buffs(self):
        """Calcula buffs activos basados en misiones completadas."""
        new_buffs = set()
        for m_id in self.completed_missions:
            for m_info in self.missions:
                if m_info["id"] == m_id and "buff" in m_info:
                    new_buffs.add(m_info["buff"])
        self.active_buffs = new_buffs

    def check_mission(self):
        """Disparador manual para verificar el progreso de la misión."""
        self._check_mission_progress()

    def _complete_mission(self, mission):
        """Marca una misión como completada y otorga recompensa."""
        if mission["id"] not in self.completed_missions:
            self.completed_missions.append(mission["id"])
            self.grant_atp(mission["reward"])
            self.current_mission_idx += 1
            self.ctx.add_log(f"🏆 MISIÓN CUMPLIDA: {mission['name']}", "mission_complete")
            print(f"🎉 [PROGRESSION] Misión completada: {mission['id']}")
            self._update_all_buffs()

    def consume_atp(self, amount: float):
        """Consume ATP por acciones (movimiento, etc)."""
        self.atp = max(0.0, self.atp - amount)

    def grant_atp(self, amount: float):
        """Otorga ATP por logros o entorno."""
        self.atp = min(self.max_atp, self.atp + amount)

    def _handle_energy_death(self):
        """El jugador se queda sin energía y colapsa."""
        self.ctx.add_log("💀 MUERTE ENERGÉTICA: Molécula colapsada.", "energy_death")
        # Reset básico del jugador
        self.ctx.player_idx = 0
        self.atp = 40.0
        
    def get_status_text(self) -> str:
        """Retorna el texto para la UI."""
        if self.current_mission_idx < len(self.missions):
            m = self.missions[self.current_mission_idx]
            status = f"Objetivo: {m['name']}"
            if m.get("needs_clay"):
                status += " (Requiere Arcilla)"
            return status
        return "Evolución prebiótica completada. ¡Fábrica Lista!"

def get_progression_manager(ctx=None):
    """Acceso singleton al manager de progresión."""
    static_vars = get_progression_manager.__dict__
    if "instance" not in static_vars:
        if ctx is None:
            from src.core.context import get_context
            ctx = get_context()
        static_vars["instance"] = ProgressionManager(ctx)
    return static_vars["instance"]
