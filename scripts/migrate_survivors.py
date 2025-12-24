import json
import os
import re

def normalize_formula(f):
    # Ensure all elements have counts (e.g. C3H4O -> C3H4O1)
    res = ""
    matches = re.finditer(r'([A-Z][a-z]?)(\d*)', f)
    for m in matches:
        elem = m.group(1)
        count = m.group(2)
        if count == "": count = "1"
        res += f"{elem}{count}"
    return res

def process_33():
    enriched_path = 'data/molecules/enriched_discoveries.json'
    precursors_path = 'data/molecules/organic/precursors.json'
    organic_exotic_path = 'data/molecules/organic/exotic.json'
    inorganic_exotic_path = 'data/molecules/inorganic/exotic.json'

    with open(enriched_path, 'r', encoding='utf-8') as f:
        enriched = json.load(f)
    
    with open(precursors_path, 'r', encoding='utf-8') as f:
        precursors = json.load(f)
        
    with open(organic_exotic_path, 'r', encoding='utf-8') as f:
        org_exotic = json.load(f)

    with open(inorganic_exotic_path, 'r', encoding='utf-8') as f:
        inorg_exotic = json.load(f)

    molecules = enriched['molecules']
    
    for f_orig, mol in molecules.items():
        f_norm = normalize_formula(f_orig)
        name = mol['identity']['names']['es']
        
        # Add Generic Lore if missing/basic
        if "biológico" in mol['lore']['biological_presence'].lower() or mol['lore']['biological_presence'] == "Trazas":
             mol['lore']['origin_story'] = f"Molécula emergente formada por la colisión y unión de fragmentos menores en condiciones de alta energía. Representa un nodo en la red química primordial."
             mol['lore']['biological_presence'] = "Intermedio reactivo en senderos metabólicos experimentales. No esencial para la vida terrestre pero posible cofactor exótico."
             mol['lore']['utility'] = "Estabilización de estructuras moleculares complejas y catálisis de reacciones de transferencia."
        
        # 1. Acrolein logic
        if "Acroleína" in name:
            # Update precursors
            precursors['molecules']['C3H4O1'] = mol
            if 'C3H4O' in precursors['molecules']:
                del precursors['molecules']['C3H4O']
            continue
            
        # 2. Organic vs Inorganic
        if 'C' in f_orig:
            org_exotic['molecules'][f_norm] = mol
        else:
            inorg_exotic['molecules'][f_norm] = mol

    # Save
    with open(precursors_path, 'w', encoding='utf-8') as f:
        json.dump(precursors, f, indent=4, ensure_ascii=False)
    with open(organic_exotic_path, 'w', encoding='utf-8') as f:
        json.dump(org_exotic, f, indent=4, ensure_ascii=False)
    with open(inorganic_exotic_path, 'w', encoding='utf-8') as f:
        json.dump(inorg_exotic, f, indent=4, ensure_ascii=False)

    # Clear enriched
    enriched['molecules'] = {}
    enriched['_meta']['total_molecules'] = 0
    with open(enriched_path, 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    print("Success: Moved 33 molecules and cleared enriched_discoveries.json")

if __name__ == "__main__":
    process_33()
