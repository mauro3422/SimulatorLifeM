#!/usr/bin/env python
"""
Script para identificar moléculas reales importantes y basura en enriched_discoveries.json
"""
import json
import re

# Moléculas reales conocidas que deberían catalogarse
REAL_MOLECULES = {
    # Ácidos orgánicos
    'C2H4O2': ('Ácido Acético', 'bio/metabolism.json'),
    'C3H4O3': ('Ácido Pirúvico', 'bio/metabolism.json'),
    'C4H6O5': ('Ácido Málico', 'bio/metabolism.json'),
    'C6H8O7': ('Ácido Cítrico', 'bio/metabolism.json'),
    'C3H6O3': ('Ácido Láctico', 'bio/metabolism.json'),
    
    # Alcoholes
    'C1H4O1': ('Metanol', 'organic/precursors.json'),
    'C2H6O1': ('Etanol', 'organic/precursors.json'),
    'C3H8O1': ('Propanol', 'organic/precursors.json'),
    
    # Aldehídos/Cetonas
    'C2H4O1': ('Acetaldehído', 'organic/precursors.json'),
    'C3H6O1': ('Acetona/Propanal', 'organic/precursors.json'),
    
    # Gases importantes
    'C1N1H1': ('HCN - Ácido Cianhídrico', 'organic/nitriles.json'),
    'H1C1N1': ('HCN - Ácido Cianhídrico', 'organic/nitriles.json'),
    
    # Otros
    'C2H6O2': ('Etilenglicol', 'organic/precursors.json'),
    'C2H3O2N1': ('Glicina', 'bio/amino_acids.json'),
}

# Patrones de basura física (radicales imposibles)
TRASH_PATTERNS = [
    r'^H1P1$',        # HP solo
    r'^H1S1$',        # HS solo  
    r'^C1H1$',        # CH solo
    r'^N1O1$',        # NO radical
    r'^P\d+$',        # Solo fósforos
    r'^S\d+$',        # Solo azufres
    r'^Si\d+$',       # Solo silicios
    # Moléculas con conteos extremos
]

def analyze_enriched():
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    found_real = []
    found_trash = []
    
    for formula, mol in data['molecules'].items():
        name = mol['identity']['names']['es']
        
        # Buscar moléculas reales
        if formula in REAL_MOLECULES:
            found_real.append((formula, name, REAL_MOLECULES[formula]))
        
        # Buscar patrones de basura
        for pattern in TRASH_PATTERNS:
            if re.match(pattern, formula):
                found_trash.append((formula, name, 'regex match'))
                break
        
        # Detectar moléculas con demasiados fósforos o azufres
        p_match = re.search(r'P(\d+)', formula)
        s_match = re.search(r'S(\d+)', formula)
        if p_match and int(p_match.group(1)) >= 4:
            found_trash.append((formula, name, 'P>=4'))
        if s_match and int(s_match.group(1)) >= 5:
            found_trash.append((formula, name, 'S>=5'))
    
    print("=== MOLECULAS REALES ENCONTRADAS ===")
    for f, n, dest in found_real:
        print(f"  {f}: {n} -> {dest}")
    
    print(f"\n=== BASURA ENCONTRADA ({len(found_trash)}) ===")
    for f, n, reason in found_trash[:20]:
        print(f"  {f}: {n} ({reason})")

if __name__ == "__main__":
    analyze_enriched()
