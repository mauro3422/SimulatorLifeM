"""
Atom Labels - Renderiza símbolos de elementos sobre los átomos.
"""

import numpy as np
from imgui_bundle import imgui
import src.config as cfg


def draw_atom_labels(pos_data, type_data, visible_indices_field, 
                     n_visible: int, camera_params, win_w: int, win_h: int,
                     show_labels: bool = True, max_labels: int = 150, alpha: float = 1.0):
    """
    Dibuja etiquetas de elementos (H, C, O) sobre los átomos visibles.
    Versión vectorizada para alto rendimiento.
    """
    if not show_labels or n_visible == 0 or pos_data is None or alpha <= 0.01:
        return
    
    # 1. Coordinate Transform (Vectorized)
    cx, cy, vis_w_half, vis_h_half = camera_params
    
    # Smooth Alpha scaling already handled by the 'alpha' parameter from FrameLoop
    
    # Slice to max_labels to avoid processing too many
    n_limit = min(n_visible, max_labels)
    
    # Prioritize CLOSEST atoms (End of Z-sorted array)
    # The array is sorted Far -> Near, so we want the last n_limit elements.
    start_idx = n_visible - n_limit
    
    # Slice taking the end of the array
    pos_subset = pos_data[start_idx:]
    type_subset = type_data[start_idx:].flatten()
    
    # World -> NDC
    # ndc_x = (wx - cx) / vis_w_half
    # ndc_y = (wy - cy) / vis_h_half
    ndc_x = (pos_subset[:, 0] - cx) / vis_w_half
    ndc_y = (pos_subset[:, 1] - cy) / vis_h_half
    
    # NDC -> Screen
    # screen_x = (ndc_x * 0.5 + 0.5) * win_w
    # screen_y = (ndc_y * 0.5 + 0.5) * win_h  <-- Fixed Y direction (Shader flips Y)
    screen_x = (ndc_x * 0.5 + 0.5) * win_w
    screen_y = (ndc_y * 0.5 + 0.5) * win_h
    
    draw_list = imgui.get_background_draw_list()
    alpha_int = int(alpha * 255)
    
    # Pre-fetch colors and symbols to avoid dict lookup in loop inside ImGui calls
    # optimization: cache dictionary lookups
    # (Optional constraint: If ImGui calls are slow, consider batching text? No easy way in immediate mode)

    padding = 2.0
    half_pad = padding * 0.5
    bg_col = imgui.IM_COL32(0, 0, 0, 180)
    
    for i in range(n_limit):
        sx, sy = screen_x[i], screen_y[i]
        
        # Culling de pantalla estricto (no dibujar si está fuera de UI)
        if sx < 0 or sx > win_w or sy < 0 or sy > win_h:
            continue
            
        # Get atom type from synced array (fixes Z-sort mismatch)
        atom_idx = int(type_subset[i])
        symbol = cfg.TIPOS_NOMBRES[atom_idx]
        
        # Color del elemento
        info = cfg.ATOMS[symbol]
        lc = info.get('label_color', [255, 255, 255])
        text_col = imgui.IM_COL32(int(lc[0]), int(lc[1]), int(lc[2]), alpha_int)
        shadow_col = imgui.IM_COL32(0, 0, 0, int(alpha_int * 0.8))
        
        # Center Text
        # Approximation: Font height is roughly 13px. Width varies.
        # ImGui calc_text_size is expensive in loop? 
        # For single char symbols (H, C, N, O), width is mostly constant.
        # Let's assume w=8, h=13 for perf? Or call calc_text_size.
        # Let's call calc_text_size for correctness but be aware.
        # Optimization: cache size per symbol?
        
        txt_w = 12.0 if len(symbol) > 1 else 8.0 # Heurisitc for labels
        txt_h = 14.0
        
        tx = sx - txt_w * 0.5
        ty = sy - txt_h * 0.5
        
        # Draw Background - REMOVED for transparency as requested
        # draw_list.add_rect_filled(
        #     (tx - padding, ty - padding),
        #     (tx + txt_w + padding, ty + txt_h + padding),
        #     bg_col, 3.0
        # )
        
        # Draw Text
        draw_list.add_text((tx + 1, ty + 1), shadow_col, symbol)
        draw_list.add_text((tx, ty), text_col, symbol)
