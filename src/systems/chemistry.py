import numpy as np
import src.config as cfg
from src.core.logger import log_bond

def check_bonding(universe, colision_mask):
    """
    Si hay colisión y ambos tienen manos libres, forman un enlace.
    Solo se enlazan si están en el rango correcto (no superpuestos).
    """
    # Calcular distancias
    diff = universe.pos[:, np.newaxis, :] - universe.pos[np.newaxis, :, :]
    dist = np.linalg.norm(diff, axis=2)
    
    # Rango de enlace: usar valores calculados científicamente del config
    rango_min = universe.config.RANGO_ENLACE_MIN
    rango_max = universe.config.RANGO_ENLACE_MAX
    
    # Solo enlazar si están en el "rango de enlace" (cerca pero no superpuestos)
    bonding_range_mask = (dist > rango_min) & (dist < rango_max)
    np.fill_diagonal(bonding_range_mask, False)
    np.fill_diagonal(bonding_range_mask, False)
    
    pares_potenciales = np.argwhere(np.triu(bonding_range_mask))
    
    for i, j in pares_potenciales:
        # Si NO están ya enlazados Y ambos tienen manos libres
        if not universe.enlaces[i, j] and universe.manos_libres[i] > 0 and universe.manos_libres[j] > 0:
            universe.enlaces[i, j] = True
            universe.enlaces[j, i] = True
            universe.manos_libres[i] -= 1
            universe.manos_libres[j] -= 1
            
            # Logging
            t1 = cfg.TIPOS_NOMBRES[universe.tipos[i]]
            t2 = cfg.TIPOS_NOMBRES[universe.tipos[j]]
            log_bond(i, j, t1, t2)

def aplicar_fuerzas_enlace(universe):
    """
    Aplica una fuerza de atracción (resorte) amortiguada entre partículas enlazadas.
    Evita que vibren infinitamente (el 'tambaleo').
    """
    if not np.any(universe.enlaces):
        return
    
    # 1. Vectores de diferencia y distancias
    diff = universe.pos[:, np.newaxis, :] - universe.pos[np.newaxis, :, :]
    dist = np.linalg.norm(diff, axis=2)
    
    # 2. Vectores de velocidad relativa (para amortiguación)
    v_diff = universe.vel[:, np.newaxis, :] - universe.vel[np.newaxis, :, :]
    
    # Máscara de enlaces
    mask = universe.enlaces
    
    if np.any(mask):
        # Evitar división por cero en las direcciones
        with np.errstate(divide='ignore', invalid='ignore'):
            direccion = diff / dist[:, :, np.newaxis]
        direccion = np.nan_to_num(direccion)
        
        # A. Fuerza de Resorte (Elástico)
        delta_x = dist - universe.config.DIST_EQUILIBRIO
        fuerza_resorte = direccion * delta_x[:, :, np.newaxis] * universe.config.SPRING_K
        
        # B. Fuerza de Amortiguación (Viscosidad del enlace)
        # Proyectamos la velocidad relativa sobre la dirección del enlace
        v_rel_proyectada = np.sum(v_diff * direccion, axis=2)
        fuerza_amortiguacion = direccion * (v_rel_proyectada[:, :, np.newaxis] * universe.config.DAMPING)
        
        # C. Fuerza Total
        fuerza_total_matrix = fuerza_resorte + fuerza_amortiguacion
        fuerza_total_matrix[~mask] = 0

        # D. Estrés de Enlace (Rotura si se estira demasiado)
        # Usar distancia de rotura del config
        dist_break = universe.config.DIST_ROTURA
        rotura_mask = (dist > dist_break) & mask
        if np.any(rotura_mask):
            pares_rotura = np.argwhere(np.triu(rotura_mask))
            for i, j in pares_rotura:
                universe.enlaces[i, j] = False
                universe.enlaces[j, i] = False
                universe.manos_libres[i] += 1
                universe.manos_libres[j] += 1
        
        # Eliminar fuerzas de enlaces que se acaban de romper
        fuerza_total_matrix[rotura_mask] = 0
        
        # Sumamos todas las fuerzas que recibe cada partícula
        fuerza_aplicada = np.sum(fuerza_total_matrix, axis=1)
        
        # Estabilidad: Limitar fuerza máxima por frame
        max_f = universe.config.MAX_FUERZA
        f_norm = np.linalg.norm(fuerza_aplicada, axis=1, keepdims=True)
        mask_f = f_norm > max_f
        # Evitar división por cero en la normalización
        f_norm[f_norm == 0] = 1.0
        fuerza_aplicada[mask_f[:, 0]] = (fuerza_aplicada[mask_f[:, 0]] / f_norm[mask_f[:, 0]]) * max_f
        
        # Aplicar fuerza (factor 0.3 para suavidad con los nuevos valores calibrados)
        universe.vel -= fuerza_aplicada * 0.3
