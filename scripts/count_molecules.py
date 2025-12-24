#!/usr/bin/env python
"""Script para contar moléculas catalogadas."""
import json
import os

files = [
    'data/molecules/bio/metabolism.json',
    'data/molecules/bio/amino_acids.json', 
    'data/molecules/bio/nucleobases.json',
    'data/molecules/bio/sugars.json',
    'data/molecules/organic/nitriles.json',
    'data/molecules/organic/hydrocarbons.json',
    'data/molecules/organic/precursors.json',
    'data/molecules/organic/exotic.json',
    'data/molecules/inorganic/vital.json',
    'data/molecules/inorganic/exotic.json',
    'data/molecules/inorganic/elements.json'
]

total = 0
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            d = json.load(file)
            count = len(d.get('molecules', {}))
            total += count
            print(f"{os.path.basename(f)}: {count}")
    except Exception as e:
        print(f"{os.path.basename(f)}: ERROR")

print(f"\nTotal catalogadas: {total}")

# Enriched count
with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
    enriched = json.load(f)
print(f"En enriched pendientes: {len(enriched['molecules'])}")

# Blocklist
with open('data/molecules/blocklist.json', 'r', encoding='utf-8') as f:
    block = json.load(f)
print(f"En blocklist: {block['total']}")
