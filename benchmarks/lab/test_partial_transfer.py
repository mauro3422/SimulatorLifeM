import taichi as ti
import time
import numpy as np

ti.init(arch=ti.vulkan)

MAX = 100000
field = ti.field(dtype=ti.f32, shape=(MAX, 6))

print(f"Probando transferencia de campo completo ({MAX} filas)...")
start = time.perf_counter()
data_full = field.to_numpy()
print(f"Tiempo total: {(time.perf_counter() - start)*1000:.2f} ms")

PARTIAL = 1000
print(f"Probando transferencia parcial ({PARTIAL} filas)...")
try:
    start = time.perf_counter()
    # En versiones recientes de Taichi, esto suele funcionar
    data_partial = field.to_numpy()[:PARTIAL] # Esto descarga todo y luege corta (Lento)
    print(f"Tiempo rebanada Python: {(time.perf_counter() - start)*1000:.2f} ms")
    
    # Intento de descarga real parcial (si el API lo soporta)
    # Algunas versiones requieren esto:
    start = time.perf_counter()
    # No hay un path directo oficial en Taichi para 'Partial Download' 
    # sin usar external_array o ndarray.
    print("Taichi to_numpy() siempre sincroniza el buffer completo.")
except Exception as e:
    print(f"Error en parcial: {e}")
