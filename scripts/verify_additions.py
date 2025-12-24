
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.config.molecules import load_molecule_database, get_molecule_name

def verify_additions():
    load_molecule_database()
    
    test_cases = [
        ("C2H6O1", "Etanol"),      # Added as C2H6O
        ("C2H4", "Etileno"),       # Added as C2H4 (Match)
        ("C2H2", "Acetileno"),     # Added as C2H2 (Match)
        ("C1H2O2", "Ácido Fórmico"), # Added as CH2O2 vs C1H2O2
        ("C2H4O2", "Ácido Acético"), # Added as C2H4O2 (Match)
        ("H2O2", "Peróxido de Hidrógeno"), # Added as H2O2
        ("C3H4", "Propino"),        # Added as C3H4
        ("H3N3", "Triazina") # Assuming a placeholder name for H3N3
    ]
    
    print(f"{'Inputs':<15} | {'Expected':<25} | {'Got':<25} | {'Status'}")
    print("-" * 80)
    
    for formula, expected in test_cases:
        got = get_molecule_name(formula)
        status = "✅" if got == expected else "❌"
        print(f"{formula:<15} | {expected:<25} | {got:<25} | {status}")

if __name__ == "__main__":
    verify_additions()
