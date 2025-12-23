"""
Bubble Labels - Renderiza fórmulas sobre las burbujas macroscópicas (LOD).
"""

import numpy as np
from imgui_bundle import imgui

def draw_bubble_labels(bubbles_data, camera_params, win_w: int, win_h: int, alpha: float = 1.0):
    """
    Dibuja etiquetas de fórmulas (H2O, CH4) sobre las burbujas LOD.
    """
    if not bubbles_data or alpha < 0.01:
        return
        
    centers = bubbles_data.get('centers')
    labels = bubbles_data.get('labels')
    
    if centers is None or labels is None or len(centers) == 0:
        return
        
    # Coordinate Transform
    cx, cy, vis_w_half, vis_h_half = camera_params
    
    # World -> NDC -> Screen
    ndc_x = (centers[:, 0] - cx) / vis_w_half
    ndc_y = (centers[:, 1] - cy) / vis_h_half
    
    screen_x = (ndc_x * 0.5 + 0.5) * win_w
    screen_y = (ndc_y * 0.5 + 0.5) * win_h
    
    draw_list = imgui.get_background_draw_list()
    
    # Limitar etiquetas para evitar saturación (Máximo 150)
    n_labels = min(len(centers), 150)
    
    for i in range(n_labels):
        sx, sy = screen_x[i], screen_y[i]
        
        # Culling
        if sx < 0 or sx > win_w or sy < 0 or sy > win_h:
            continue
            
        label = labels[i]
        
        # Calcular opacidad basada en distancia al centro (0.0 a 1.0)
        dist_x = abs(sx / win_w - 0.5) * 2.0
        dist_y = abs(sy / win_h - 0.5) * 2.0
        dist_center = max(dist_x, dist_y)
        local_alpha = max(0, 1.0 - dist_center**2)
        
        # Alpha final combinando cross-fade global y culling local
        final_alpha_int = int(local_alpha * alpha * 255)
        
        if final_alpha_int < 20: continue
        
        white = imgui.IM_COL32(255, 255, 255, final_alpha_int)
        shadow = imgui.IM_COL32(0, 0, 0, int(final_alpha_int * 0.8))
        
        # Calcular tamaño del texto para centrar
        txt_size = imgui.calc_text_size(label)
        tx = sx - txt_size.x * 0.5
        ty = sy - txt_size.y * 0.5
        
        # Dibujar sombra (mejor legibilidad)
        draw_list.add_text((tx + 1, ty + 1), shadow, label)
        # Dibujar texto principal
        draw_list.add_text((tx, ty), white, label)
