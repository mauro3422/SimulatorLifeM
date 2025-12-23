"""
Shader Sources - GLSL Shaders para ParticleRenderer
=====================================================
Centraliza todos los shaders GLSL usados para rendering.
Permite editar shaders sin modificar lógica de rendering.
"""

# ===================================================================
# PARTÍCULAS - Shader con efecto 2.5D Depth + Desaturación
# ===================================================================

PARTICLE_VERTEX = '''
#version 330
in vec2 in_vert;
in vec3 in_color;
in float in_scale;  // 2.5D depth scale (0.4 to 1.6)
out vec3 v_color;
out float v_depth_factor;  // Para desaturación en fragment
uniform vec2 u_offset;
uniform vec2 u_scale;
uniform float u_base_size;

void main() {
    vec2 pos_ndc = (in_vert - u_offset) * u_scale;
    gl_Position = vec4(pos_ndc.x, -pos_ndc.y, 0.0, 1.0);
    
    // Tamaño con efecto de profundidad
    gl_PointSize = u_base_size * in_scale;
    v_color = in_color;
    
    // Factor de profundidad: <1 = lejos (desaturar), >1 = cerca (saturar)
    v_depth_factor = in_scale;
}
'''

PARTICLE_FRAGMENT = '''
#version 330
in vec3 v_color;
in float v_depth_factor;
out vec4 f_color;
uniform float u_global_alpha;

void main() {
    float dist = length(gl_PointCoord - 0.5);
    if (dist > 0.5) discard;
    
    // Glow para átomos cercanos (depth_factor > 1.1)
    float glow_intensity = clamp((v_depth_factor - 1.0) * 2.0, 0.0, 0.4);
    float glow_alpha = smoothstep(0.5, 0.35, dist) * glow_intensity;
    
    float alpha = smoothstep(0.5, 0.45, dist);
    float center = smoothstep(0.2, 0.0, dist);
    vec3 base_col = v_color * (0.8 + 0.2 * center);
    
    // Desaturación por profundidad
    float gray = dot(base_col, vec3(0.299, 0.587, 0.114));
    float desat = clamp((1.0 - v_depth_factor) * 0.8, 0.0, 0.6);
    vec3 final_col = mix(base_col, vec3(gray), desat);
    
    // Oscurecer lejanos, iluminar cercanos
    final_col *= (0.7 + 0.3 * v_depth_factor);
    
    // Agregar glow blanco suave a cercanos
    final_col += vec3(glow_alpha * 0.5);
    
    f_color = vec4(final_col, (alpha + glow_alpha) * u_global_alpha);
}
'''


# ===================================================================
# ENLACES - Shader simple para líneas
# ===================================================================

BOND_VERTEX = '''
#version 330
in vec2 in_vert;
uniform vec2 u_offset;
uniform vec2 u_scale;

void main() {
    vec2 pos_ndc = (in_vert - u_offset) * u_scale;
    gl_Position = vec4(pos_ndc.x, -pos_ndc.y, 0.0, 1.0);
}
'''

BOND_FRAGMENT = '''
#version 330
uniform vec4 color;
uniform float u_global_alpha;
out vec4 f_color;
void main() {
    f_color = vec4(color.rgb, color.a * u_global_alpha);
}
'''


# ===================================================================
# ANILLOS SDF - Shader con efecto de anillo
# ===================================================================

RING_VERTEX = '''
#version 330
in vec2 in_vert;
uniform vec2 u_offset;
uniform vec2 u_scale;
uniform float u_radius_world;
uniform float u_px_scale_y; // height / 2.0

void main() {
    vec2 pos_ndc = (in_vert - u_offset) * u_scale;
    gl_Position = vec4(pos_ndc.x, -pos_ndc.y, 0.0, 1.0);
    
    // Calcular tamaño en pixeles para cubrir el radio del mundo
    float diam_px = (u_radius_world * u_scale.y) * u_px_scale_y * 2.0;
    gl_PointSize = diam_px + 4.0; // +4 padding para antialiasing
}
'''

RING_FRAGMENT = '''
#version 330
uniform vec4 color;
uniform float u_global_alpha;
out vec4 f_color;
void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv) * 2.0; // 0..1 (donde 1 es borde del point size)
    
    // SDF del anillo
    float thickness = 0.15;
    float alpha = smoothstep(1.0, 0.8, dist) * smoothstep(0.8 - thickness - 0.1, 0.8 - thickness, dist);
    
    if (alpha < 0.01) discard;
    f_color = vec4(color.rgb, color.a * alpha * u_global_alpha);
}
'''


# ===================================================================
# ANILLOS COLOREADOS - Per-instance color
# ===================================================================

RING_COLORED_VERTEX = '''
#version 330
in vec2 in_vert;
in vec4 in_color; // RGBA per instance
out vec4 v_color;

uniform vec2 u_offset;
uniform vec2 u_scale;
uniform float u_radius_world;
uniform float u_px_scale_y; 

void main() {
    vec2 pos_ndc = (in_vert - u_offset) * u_scale;
    gl_Position = vec4(pos_ndc.x, -pos_ndc.y, 0.0, 1.0);
    
    float diam_px = (u_radius_world * u_scale.y) * u_px_scale_y * 2.0;
    gl_PointSize = diam_px + 4.0; 
    v_color = in_color;
}
'''

RING_COLORED_FRAGMENT = '''
#version 330
in vec4 v_color;
uniform float u_global_alpha;
out vec4 f_color;
void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv) * 2.0;
    
    float thickness = 0.15;
    float alpha = smoothstep(1.0, 0.8, dist) * smoothstep(0.8 - thickness - 0.1, 0.8 - thickness, dist);
    
    if (alpha < 0.01) discard;
    f_color = vec4(v_color.rgb, v_color.a * alpha * u_global_alpha);
}
'''


# ===================================================================
# BURBUJAS LOD - Filled Circles con Per-Instance Radius
# ===================================================================

BUBBLE_VERTEX = '''
#version 330
in vec2 in_vert;
in vec4 in_color;
in float in_radius;
out vec4 v_color;

uniform vec2 u_offset;
uniform vec2 u_scale;
uniform float u_px_scale_y; 

void main() {
    vec2 pos_ndc = (in_vert - u_offset) * u_scale;
    gl_Position = vec4(pos_ndc.x, -pos_ndc.y, 0.0, 1.0);
    
    float diam_px = (in_radius * u_scale.y) * u_px_scale_y * 2.0;
    gl_PointSize = max(diam_px + 2.0, 4.0);
    v_color = in_color;
}
'''

BUBBLE_FRAGMENT = '''
#version 330
in vec4 v_color;
uniform float u_global_alpha;
out vec4 f_color;
void main() {
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv) * 2.0;
    
    // Filled circle with soft edge
    float alpha = smoothstep(1.0, 0.85, dist);
    
    if (alpha < 0.01) discard;
    f_color = vec4(v_color.rgb, v_color.a * alpha * u_global_alpha);
}
'''
