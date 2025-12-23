"""
Análisis de Formación de Bases Nitrogenadas
============================================
Verifica si A, T, G, C se forman naturalmente en la simulación.
"""
import json

# Cargar moléculas desconocidas
with open('data/unknown_molecules.json', 'r') as f:
    unknown_data = json.load(f)

# Bases nitrogenadas objetivo
BASES = {
    'C5H5N5': 'Adenina (A)',
    'C5H5N5O1': 'Guanina (G)', 
    'C4H5N3O1': 'Citosina (C)',
    'C5H6N2O2': 'Timina (T)',
    'C4H4N2O2': 'Uracilo (U) - ARN',
}

# Otras moléculas prebióticas importantes
PREBIOTIC = {
    'C5H10O5': 'Ribosa',
    'C5H10O4': 'Desoxirribosa',
    'H3O4P1': 'Ácido Fosfórico',
    'C2H5N1O2': 'Glicina',
    'C3H7N1O2': 'Alanina',
}

molecules = unknown_data.get('molecules', {})

print("=" * 60)
print("ANÁLISIS DE FORMACIÓN MOLECULAR")
print("=" * 60)
print(f"Total moléculas desconocidas: {unknown_data['count']}")

print("\n--- BASES NITROGENADAS (ADN/ARN) ---")
for formula, name in BASES.items():
    if formula in molecules:
        count = molecules[formula].get('discovery_count', 0)
        print(f"  ✅ {name} ({formula}): {count} veces")
    else:
        print(f"  ❌ {name} ({formula}): NO DETECTADA")

print("\n--- PRECURSORES PREBIÓTICOS ---")
for formula, name in PREBIOTIC.items():
    if formula in molecules:
        count = molecules[formula].get('discovery_count', 0)
        print(f"  ✅ {name} ({formula}): {count} veces")
    else:
        print(f"  ❌ {name} ({formula}): NO DETECTADA")

# Buscar moléculas con patrones interesantes (alto N, presencia de P)
print("\n--- MOLÉCULAS CON NITRÓGENO ALTO (N>=3) ---")
high_n = []
for formula, data in molecules.items():
    if 'N' in formula:
        # Extraer cantidad de N
        import re
        n_match = re.search(r'N(\d+)', formula)
        if n_match:
            n_count = int(n_match.group(1))
            if n_count >= 3:
                high_n.append((formula, data.get('discovery_count', 0)))

high_n.sort(key=lambda x: x[1], reverse=True)
for formula, count in high_n[:10]:
    print(f"  {formula}: {count} veces")

print("\n--- MOLÉCULAS CON FÓSFORO (P) ---")
phosphorus = []
for formula, data in molecules.items():
    if 'P' in formula:
        phosphorus.append((formula, data.get('discovery_count', 0)))

phosphorus.sort(key=lambda x: x[1], reverse=True)
for formula, count in phosphorus[:10]:
    print(f"  {formula}: {count} veces")

print("\n--- TOP 15 MOLÉCULAS MÁS FRECUENTES ---")
all_mols = [(f, d.get('discovery_count', 0)) for f, d in molecules.items()]
all_mols.sort(key=lambda x: x[1], reverse=True)
for formula, count in all_mols[:15]:
    print(f"  {formula}: {count} veces")
