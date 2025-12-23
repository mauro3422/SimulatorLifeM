"""
Physics Verification Script
===========================
Verifica que las constantes físicas tengan sentido a la escala de simulación.
Simula un entorno mínimo de prueba sin gráficos.
"""
import sys
import os
import math

# Add source to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.systems.physics_constants import (
    VDW_K, VDW_RANGE_FACTOR, 
    SPRING_K_DEFAULT, DIST_EQUILIBRIO_BASE,
    COULOMB_K, REPULSION_MIN_DIST
)

def verify_vdw_vs_bond():
    """Comparar fuerza Van der Waals vs Enlaces Covalentes."""
    print(f"\n[VERIFY] Intermolecular Forces (VDW) vs Intramolecular (Bond)")
    print(f"-------------------------------------------------------------")
    
    # 1. Fuerza de Enlace (Spring) a 10% de estiramiento
    dist_eq = DIST_EQUILIBRIO_BASE * 3.0 # Assuming scale 3.0
    dist_stretch = dist_eq * 1.1
    f_bond = SPRING_K_DEFAULT * (dist_stretch - dist_eq)
    
    # 2. Fuerza VDW a distancia óptima (aprox 1.5 radios)
    # Radio real aprox: (10 * 1.5 + 5) * 3.0 = 60.0 px
    radius = 60.0
    dist_vdw = radius * 2.5
    cutoff = radius * VDW_RANGE_FACTOR
    
    # Simple linear approximation from kernel
    strength = 1.0 - (dist_vdw - (radius*2)) / (cutoff - (radius*2))
    f_vdw = VDW_K * strength
    
    print(f"Fuerza Enlace (Covalente):  {f_bond:.2f}")
    print(f"Fuerza VDW (Líquido):       {f_vdw:.2f}")
    
    ratio = f_bond / (f_vdw + 0.0001)
    print(f"Ratio (Bond/VDW): {ratio:.2f}x")
    
    if ratio < 5.0:
        print("⚠️  ADVERTENCIA: La fuerza VDW es muy fuerte comparada con los enlaces.")
        print("    Podría romper moléculas o causar inestabilidad.")
    elif ratio > 100.0:
        print("⚠️  ADVERTENCIA: La fuerza VDW es insignificante.")
        print("    No se formarán líquidos/gotas.")
    else:
        print("✅  La relación de fuerzas es saludable (5x - 100x).")

def verify_scales():
    """Verificar escalas espaciales."""
    print(f"\n[VERIFY] Spatial Scales")
    print(f"-----------------------")
    
    radius = 60.0
    vdw_range = radius * VDW_RANGE_FACTOR
    bond_len = DIST_EQUILIBRIO_BASE * 3.0
    
    print(f"Radio Atómico:      {radius} px")
    print(f"Longitud Enlace:    {bond_len} px")
    print(f"Rango VDW:          {vdw_range} px")
    
    if vdw_range < bond_len:
         print("⚠️  ADVERTENCIA: El rango VDW es menor que la longitud de enlace.")
         print("    Las moléculas no se atraerán entre sí efectivamente.")
    else:
        print(f"✅  Rango VDW cubre {(vdw_range/bond_len):.2f}x la longitud de un enlace.")

def verify_force_balance():
    """Analizar balance de fuerzas en diferentes distancias."""
    print(f"\n[VERIFY] Force Balance Analysis")
    print(f"-------------------------------")
    print(f"{'Dist (px)':<10} | {'VDW (Attr)':<12} | {'Coulomb (Rep)':<12} | {'Net Force':<12} | {'Status'}")
    print("-" * 65)

    radius = 60.0 # From previous step
    cutoff = radius * VDW_RANGE_FACTOR
    
    # Test distances: From close (collision) to far (cutoff)
    distances = [radius, radius*1.1, radius*1.5, radius*2.0, radius*2.5, radius*3.0]
    
    for dist in distances:
        # 1. VDW Force
        sum_radii = radius * 2
        if dist > sum_radii and dist < cutoff:
            strength = 1.0 - (dist - sum_radii) / (cutoff - sum_radii)
            f_vdw = -VDW_K * strength # Negative = Attraction
        else:
            f_vdw = 0.0

        # 2. Coulomb Force (Assuming slight charge)
        # q = (3.0 - 2.82) * 0.2 ~ 0.036 -> q^2 ~ 0.001
        # F = k * q^2 / r^2
        q_prod = 0.001 
        f_coulomb = COULOMB_K * q_prod / (dist**2 / 100.0) # Scaling factor approx
        # Simplification: Just test generic weak repulsion
        f_coulomb = 0.05 if dist < radius * 2 else 0.01

        # 3. Brownian Kick (Random noise magnitude)
        # v_rms ~ sqrt(0.1 * 1.0 / 1.0) ~ 0.3
        # force ~ mass * accel ~ 1.0 * (v / dt) ~ 0.3
        f_brownian = 0.3

        net_force = f_vdw + f_coulomb

        status = ""
        if abs(f_vdw) > f_brownian:
            status = "CAPTURED (Liquid)"
        elif abs(f_vdw) < f_brownian:
            status = "ESCAPING (Gas)"
            
        print(f"{dist:<10.1f} | {f_vdw:<12.4f} | {f_coulomb:<12.4f} | {net_force:<12.4f} | {status}")

if __name__ == "__main__":
    verify_vdw_vs_bond()
    verify_scales()
    verify_force_balance()
