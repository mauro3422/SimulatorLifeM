#!/usr/bin/env python
"""Script para limpiar enriched_discoveries.json removiendo moléculas ya catalogadas."""
import json

def main():
    # Cargar archivos de categoría
    category_files = [
        'data/molecules/bio/metabolism.json',
        'data/molecules/bio/amino_acids.json', 
        'data/molecules/bio/nucleobases.json',
        'data/molecules/bio/sugars.json',
        'data/molecules/organic/nitriles.json',
        'data/molecules/organic/hydrocarbons.json',
        'data/molecules/organic/precursors.json',
        'data/molecules/organic/exotic.json',
        'data/molecules/organic/aggregates.json',
        'data/molecules/inorganic/vital.json',
        'data/molecules/inorganic/exotic.json',
        'data/molecules/inorganic/elements.json'
    ]

    catalogued = set()
    for filepath in category_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'molecules' in data:
                    catalogued.update(data['molecules'].keys())
        except Exception as e:
            print(f"  Skipped {filepath}: {e}")

    print(f"Total moléculas catalogadas en archivos: {len(catalogued)}")

    # Cargar enriched
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        enriched = json.load(f)

    initial_count = len(enriched['molecules'])
    
    # Remover las que ya están catalogadas
    removed = []
    for formula in list(enriched['molecules'].keys()):
        if formula in catalogued:
            del enriched['molecules'][formula]
            removed.append(formula)

    # Actualizar meta
    enriched['_meta']['total_molecules'] = len(enriched['molecules'])

    # Guardar
    with open('data/molecules/enriched_discoveries.json', 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    print(f"Removidas {len(removed)} moléculas ya catalogadas")
    print(f"Antes: {initial_count} -> Ahora: {len(enriched['molecules'])}")
    
    if removed:
        print("Moléculas removidas:")
        for r in removed[:30]:
            print(f"  - {r}")
        if len(removed) > 30:
            print(f"  ... y {len(removed)-30} más")

if __name__ == "__main__":
    main()
