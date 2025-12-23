"""
Player Indicator - Visual identity for the player atom ("Atomic Farmer").
"""

import numpy as np
import time
import math
from imgui_bundle import imgui
import src.config as cfg

def draw_player_indicator(player_idx, pos_gpu, camera_params, win_w: int, win_h: int, frame_idx: int = 0, total_frames: int = 1):
    """
    Draws a visual indicator (Atomic Farmer) above the player's atom.
    Supports sprite sheets via frame_idx and total_frames.
    """
    if player_idx < 0 or pos_gpu is None:
        return
        
    # 1. Get player position from GPU
    # Optimization: Only get the player's position, not the whole array
    # However, since we already have the array in render_data['pos'], we use that
    pos_all = pos_gpu.to_numpy()
    if player_idx >= len(pos_all):
        return
        
    px, py = pos_all[player_idx]
    
    # 2. Project World -> Screen
    cx, cy, vis_w_half, vis_h_half = camera_params
    
    ndc_x = (px - cx) / vis_w_half
    ndc_y = (py - cy) / vis_h_half
    
    sx = (ndc_x * 0.5 + 0.5) * win_w
    sy = (ndc_y * 0.5 + 0.5) * win_h
    
    # Culling
    if sx < -100 or sx > win_w + 100 or sy < -100 or sy > win_h + 100:
        return
        
    draw_list = imgui.get_foreground_draw_list()
    t = time.time()
    
    # 3. Draw Animated Halo (Glowing Ring)
    inner_radius = 15.0
    outer_radius = 20.0 + math.sin(t * 5.0) * 5.0
    
    # Pulsing color (Golden/Cyan)
    pulse = (math.sin(t * 3.0) + 1.0) * 0.5
    color_inner = imgui.IM_COL32(255, 215, 0, 180) # Gold
    color_outer = imgui.IM_COL32(0, 255, 255, int(pulse * 100)) # Cyan glow
    
    # draw_list.add_circle((sx, sy), inner_radius, color_inner, num_segments=32, thickness=2.0)
    for i in range(3):
        r = inner_radius + i * 5.0 + math.sin(t * 4.0 + i) * 2.0
        alpha = int(200 / (i + 1))
        col = imgui.IM_COL32(100, 200, 255, alpha)
        draw_list.add_circle((sx, sy), r, col, num_segments=32, thickness=1.5)

    # 4. Draw "Atomic Farmer" Sprite
    tex_data = get_player_texture_data()
    
    # Floating animation
    off_y = -45.0 + math.sin(t * 2.0) * 8.0
    
    if tex_data is not None:
        tex_id, width, height = tex_data
        
        # Calculate size maintaining aspect ratio
        frame_width = width / total_frames
        base_h = 64.0
        aspect = frame_width / height
        w = base_h * aspect
        h = base_h
        
        p_min = imgui.ImVec2(sx - w * 0.5, sy + off_y - h * 0.5)
        p_max = imgui.ImVec2(sx + w * 0.5, sy + off_y + h * 0.5)
        
        # Calculate UV range for the current frame
        uv_min = imgui.ImVec2(frame_idx / total_frames, 0)
        uv_max = imgui.ImVec2((frame_idx + 1) / total_frames, 1)
        
        # Render Sprite using ImTextureRef
        draw_list.add_image(imgui.ImTextureRef(int(tex_id)), p_min, p_max, uv_min, uv_max)
    else:
        # Fallback to Text (Emoji might not render without font support)
        # Usamos texto ASCII seguro si falla la textura
        text_icon = "[ FARMER ]"
        txt_size = imgui.calc_text_size(text_icon)
        
        # Draw background box for visibility
        draw_list.add_rect_filled(
            imgui.ImVec2(sx - txt_size.x * 0.5 - 4, sy + off_y - 2),
            imgui.ImVec2(sx + txt_size.x * 0.5 + 4, sy + off_y + 16),
            imgui.IM_COL32(0, 0, 0, 150),
            4.0
        )
        
        draw_list.add_text(
            imgui.ImVec2(sx - txt_size.x * 0.5, sy + off_y), 
            imgui.IM_COL32(0, 255, 0, 255),  # Green text
            text_icon
        )
    
    # 5. Label (Element Name + "YOU")
    label = "GRANJERO"
    label_size = imgui.calc_text_size(label)
    draw_list.add_text(
        imgui.ImVec2(sx - label_size.x * 0.5, sy + off_y + 40.0),
        imgui.IM_COL32(255, 255, 100, 255),
        label
    )

# =========================================================
# Texture Loading Helper
# =========================================================
_PLAYER_TEXTURE_DATA = None # stores (id, w, h)
_TEXTURE_LOAD_FAILED = False

def reload_player_texture():
    """Forces the texture to be reloaded on the next context access."""
    global _PLAYER_TEXTURE_DATA, _TEXTURE_LOAD_FAILED
    _PLAYER_TEXTURE_DATA = None
    _TEXTURE_LOAD_FAILED = False

def get_player_texture_data():
    global _PLAYER_TEXTURE_DATA, _TEXTURE_LOAD_FAILED
    
    if _PLAYER_TEXTURE_DATA is not None:
        return _PLAYER_TEXTURE_DATA
        
    if _TEXTURE_LOAD_FAILED:
        return None
        
    import os
    from PIL import Image
    try:
        # Check standard paths
        cwd = os.getcwd()
        paths = [
            os.path.join(cwd, "assets/images/atomic_farmer.png"),
            os.path.join(cwd, "assets", "images", "atomic_farmer.png"),
            "assets/images/atomic_farmer.png",
            "../assets/images/atomic_farmer.png",
            "atomic_farmer.png"
        ]
        
        img_path = None
        for p in paths:
            if os.path.exists(p):
                img_path = p
                print(f"[TEXTURE] Found sprite at: {p}")
                break
        
        if not img_path:
            print(f"[WARN] Sprite texture not found. Searched in: {paths}")
            _TEXTURE_LOAD_FAILED = True
            return None
            
        # Load Image
        image = Image.open(img_path)
        image = image.convert('RGBA')
        width, height = image.size
        data = image.tobytes()
        
        # Upload to OpenGL
        # NOTE: We assume an active OpenGL context exists (ImGui/ModernGL)
        from OpenGL import GL
        
        tex_id = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, tex_id)
        
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST) # Pixel art style
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, width, height, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, data)
        
        _PLAYER_TEXTURE_DATA = (tex_id, width, height)
        print(f"[TEXTURE] Loaded player sprite: {img_path} ({width}x{height})")
        return _PLAYER_TEXTURE_DATA
        
    except ImportError:
        print("[ERROR] PIL or OpenGL not available for texture loading.")
        _TEXTURE_LOAD_FAILED = True
        return None
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to load texture: {e}")
        traceback.print_exc()
        _TEXTURE_LOAD_FAILED = True
        return None
