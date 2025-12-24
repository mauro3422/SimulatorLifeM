#!/usr/bin/env python
"""
Script para auditar enriched_discoveries.json:
- Identifica moléculas con nombres genéricos (basura)
- Las mueve al blocklist
- Las remueve de enriched_discoveries
"""
import json
import re

def is_generic_trash(formula, name):
    """Detecta si una molécula tiene nombre genérico (generado automáticamente)."""
    
    # Nombres genéricos típicos del sistema
    generic_patterns = [
        r'^Met-',           # Met-aminoal, Met-fosfoal, etc
        r'^Et-',            # Et-aminoina, etc
        r'^Prop-',          # Prop-tritiooico, etc
        r'-amino',          # *-aminoal, *-aminoano
        r'-fosfo',          # *-fosfoal, *-fosfoano
        r'-tio',            # Tio-aminoano
        r'oico$',           # Metoico, Propoico
        r'oal$',            # Met-fosfoal
        r'oano$',           # Fosfoano
        r'ina$',            # Et-aminoina, Fosfoina
        r'^Radical-',       # Radical-H2P3S1
        r'^Compuesto-',     # Compuesto-h1o2
        r'^Difosfo',        # Difosfoal
        r'^Trifosfo',       # Trifosfoano
    ]
    
    name_lower = name.lower()
    
    for pattern in generic_patterns:
        if re.search(pattern.lower(), name_lower):
            return True
    
    # Si el nombre es igual a la fórmula = genérico
    if name == formula:
        return True
    
    # Si tiene caracteres muy raros
    if name.count('-') > 2:
        return True
        
    return False

def main():
    # Cargar enriched
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        enriched = json.load(f)
    
    # Cargar blocklist
    with open('data/molecules/blocklist.json', 'r', encoding='utf-8') as f:
        blocklist = json.load(f)
    
    blocked_set = set(blocklist['blocked_formulas'])
    
    # Identificar basura
    trash = []
    keep = {}
    
    for formula, mol in enriched['molecules'].items():
        name_es = mol['identity']['names']['es']
        
        if is_generic_trash(formula, name_es):
            trash.append((formula, name_es))
            blocked_set.add(formula)
        else:
            keep[formula] = mol
    
    print(f"=== AUDITORÍA enriched_discoveries.json ===")
    print(f"Total moléculas: {len(enriched['molecules'])}")
    print(f"Basura genérica detectada: {len(trash)}")
    print(f"Válidas a mantener: {len(keep)}")
    
    print(f"\n=== BASURA A MOVER A BLOCKLIST (primeras 30) ===")
    for formula, name in trash[:30]:
        print(f"  {formula}: {name}")
    
    if len(trash) > 30:
        print(f"  ... y {len(trash)-30} más")
    
    print(f"\n=== VÁLIDAS A MANTENER (muestra) ===")
    count = 0
    for formula, mol in keep.items():
        name = mol['identity']['names']['es']
        print(f"  {formula}: {name}")
        count += 1
        if count >= 20:
            break
    
    # Preguntar confirmación
    response = input("\n¿Aplicar cambios? (s/n): ")
    if response.lower() == 's':
        # Actualizar enriched
        enriched['molecules'] = keep
        enriched['_meta']['total_molecules'] = len(keep)
        
        with open('data/molecules/enriched_discoveries.json', 'w', encoding='utf-8') as f:
            json.dump(enriched, f, indent=4, ensure_ascii=False)
        
        # Actualizar blocklist
        blocklist['blocked_formulas'] = sorted(list(blocked_set))
        blocklist['total'] = len(blocked_set)
        
        with open('data/molecules/blocklist.json', 'w', encoding='utf-8') as f:
            json.dump(blocklist, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Cambios aplicados")
        print(f"  Enriched: {len(keep)} moléculas")
        print(f"  Blocklist: {len(blocked_set)} fórmulas")
    else:
        print("Cancelado")

if __name__ == "__main__":
    main()
