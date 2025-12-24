import sys
import os

# Ajustar path para importar módulos del proyecto
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.config.molecules import get_molecule_name, load_molecule_database, get_molecule_entry

def verify_quimidex_logic():
    print("--- Verificando Lógica de Quimidex/Moléculas ---")
    
    # 1. Cargar Base de Datos
    load_molecule_database("es")
    
    # 2. Verificar casos conocidos
    test_cases = [
        ("H2O", "Agua"),       # Base de datos (normal)
        ("H2O1", "Agua"),      # In-Game (explícito) vs DB (implícito) - EL BUG PRINCIPAL
        ("C1H4", "Metano"),    # Si existiera metano en DB como CH4
        ("C2H6O1", "Etanol")   # Si existiera etanol en DB como C2H6O
    ]
    
    failures = 0
    for formula, expected_name in test_cases:
        entry = get_molecule_entry(formula)
        name = get_molecule_name(formula)
        
        found = entry is not None
        match = expected_name.lower() in name.lower()
        
        status = "✅" if found and match else "❌"
        if not (found and match):
             # Don't fail immediately if it's just missing from DB but logic works, 
             # but here we expect H2O/H2O1 to definitely exist.
             if formula.startswith("H2O"):
                 failures += 1
        
        print(f"{status} Fórmula: {formula.ljust(10)} | Nombre: {name.ljust(20)} | Entry Found: {found}")

    if failures == 0:
        print("\n✅ VERIFICACIÓN EXITOSA: La lógica de normalización (H2O1 -> H2O) funciona.")
    else:
        print("\n❌ FALLO: H2O1 no se resolvió correctamente a Agua.")

if __name__ == "__main__":
    verify_quimidex_logic()
