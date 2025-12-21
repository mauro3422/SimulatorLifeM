"""
Sistema de Logging Mejorado para QuimicPYTHON
============================================
- Rotación automática (máximo 2 sesiones)
- Métricas de física (overlaps, jitter, teleports)
- Formato limpio para análisis
"""
import logging
import os
import glob
from datetime import datetime

# Crear carpeta de logs si no existe
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# --- ROTACIÓN DE LOGS (mantener solo 2 sesiones) ---
def cleanup_old_logs(max_sessions=2):
    """Elimina logs antiguos, manteniendo solo las últimas N sesiones."""
    pattern = os.path.join(LOG_DIR, "sim_*.log")
    files = glob.glob(pattern)
    if len(files) > max_sessions:
        # Ordenar por fecha de modificación (más antiguo primero)
        files.sort(key=os.path.getmtime)
        # Eliminar los más antiguos
        for old_file in files[:-max_sessions]:
            try:
                os.remove(old_file)
            except Exception:
                pass

# Limpiar antes de crear nuevo log
cleanup_old_logs(max_sessions=2)

# Configuración del logger
log_filename = os.path.join(LOG_DIR, f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Crear logger personalizado
logger = logging.getLogger("LifeSimulator")
logger.setLevel(logging.DEBUG)

# Handler para archivo (todo)
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

# Handler para consola (solo INFO y superior)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- FUNCIONES DE LOGGING ---

def log_event(message, level="info"):
    if level == "debug":
        logger.debug(message)
    elif level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)

# --- EVENTOS DE SIMULACIÓN ---

def log_bond(id1, id2, type1, type2):
    log_event(f"ENLACE: {type1}({id1}) <--> {type2}({id2})")

def log_bond_break(id1, id2, type1, type2, reason="stretch"):
    log_event(f"ROTURA: {type1}({id1}) -X- {type2}({id2}) [{reason}]", level="warning")

def log_reset():
    log_event("RESET: Universo reiniciado")

def log_stability(issue_type, magnitude):
    log_event(f"ESTABILIDAD: {issue_type} (Intensidad: {magnitude:.2f})", level="warning")

# --- MÉTRICAS DE FÍSICA (DEBUG) ---

def log_physics_frame(frame_num, n_overlaps, max_velocity, avg_bond_stretch):
    """Log detallado de física (solo a archivo, no consola)."""
    log_event(
        f"PHYSICS: frame={frame_num} overlaps={n_overlaps} max_v={max_velocity:.2f} bond_stretch={avg_bond_stretch:.2f}",
        level="debug"
    )

def log_teleport(particle_id, distance, pos_before, pos_after):
    """Detecta y registra teleportaciones (movimientos > umbral)."""
    log_event(
        f"TELEPORT: P{particle_id} movió {distance:.1f}px ({pos_before[0]:.0f},{pos_before[1]:.0f}) -> ({pos_after[0]:.0f},{pos_after[1]:.0f})",
        level="warning"
    )

def log_collision_stats(n_pairs_checked, n_collisions_found, time_ms):
    """Estadísticas de colisiones para debugging de rendimiento."""
    log_event(
        f"COLLISION: checked={n_pairs_checked} found={n_collisions_found} time={time_ms:.1f}ms",
        level="debug"
    )

def log_bond_jitter(bond_id, i, j, stretch_history):
    """Detecta vibración excesiva en enlaces."""
    if len(stretch_history) >= 5:
        variance = sum((x - sum(stretch_history)/len(stretch_history))**2 for x in stretch_history) / len(stretch_history)
        if variance > 10:  # Umbral de vibración
            log_event(f"JITTER: Enlace {i}-{j} vibrando (var={variance:.2f})", level="warning")
