#!/usr/bin/env python
"""
Script para limpiar moléculas con fórmulas físicamente imposibles o nombres incorrectos.
"""
import json
import re

def is_impossible_formula(formula, name):
    """Detecta fórmulas físicamente imposibles."""
    
    # Extraer conteos
    c = int(re.search(r'C(\d+)', formula).group(1)) if 'C' in formula else 0
    h = int(re.search(r'H(\d+)', formula).group(1)) if 'H' in formula else 0
    n = int(re.search(r'N(\d+)', formula).group(1)) if 'N' in formula else 0
    o = int(re.search(r'O(\d+)', formula).group(1)) if 'O' in formula else 0
    
    # Reglas de valencia básicas
    # Para hidrocarburos saturados: H = 2C + 2
    # Mínimo H para un hidrocarburo: ~C para insaturados
    
    # C1H1 es imposible - carbono necesita al menos 2 enlaces
    if c == 1 and h == 1 and n == 0 and o == 0:
        return True, "CH imposible"
    
    # C2H1 es imposible
    if c == 2 and h == 1 and n == 0 and o == 0:
        return True, "C2H imposible"
    
    # C1H2 sin O/N es carbeno (muy inestable)
    if c == 1 and h == 2 and n == 0 and o == 0:
        return True, "CH2 carbeno"
    
    # Nombres que no coinciden con fórmula
    name_lower = name.lower()
    
    # "Metano" debería ser CH4, no C1H1
    if 'metano' in name_lower and formula != 'C1H4' and formula != 'CH4':
        return True, "Metano incorrecto"
    
    # "Etano" debería ser C2H6
    if 'etano' in name_lower and formula != 'C2H6':
        return True, "Etano incorrecto"
    
    # Nombre genérico como "Metal", "Butato", etc
    generic_single_words = ['metal', 'butato', 'pentato', 'hexato', 'propato']
    if name_lower in generic_single_words:
        return True, "Nombre genérico"
    
    # Fórmulas sin H y pocos átomos (radicales inestables)
    total = c + h + n + o
    if h == 0 and total <= 4 and c >= 1:
        return True, "Sin H, muy inestable"
    
    return False, ""

def main():
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        enriched = json.load(f)
    
    with open('data/molecules/blocklist.json', 'r', encoding='utf-8') as f:
        blocklist = json.load(f)
    
    blocked_set = set(blocklist['blocked_formulas'])
    
    trash = []
    keep = {}
    
    for formula, mol in enriched['molecules'].items():
        name_es = mol['identity']['names']['es']
        
        is_bad, reason = is_impossible_formula(formula, name_es)
        
        if is_bad:
            trash.append((formula, name_es, reason))
            blocked_set.add(formula)
        else:
            keep[formula] = mol
    
    print(f"=== LIMPIEZA DE FÓRMULAS IMPOSIBLES ===")
    print(f"Total: {len(enriched['molecules'])}")
    print(f"Imposibles/incorrectas: {len(trash)}")
    print(f"Válidas: {len(keep)}")
    
    print(f"\n=== BASURA DETECTADA ===")
    for formula, name, reason in trash:
        print(f"  {formula}: {name} ({reason})")
    
    # Aplicar cambios
    enriched['molecules'] = keep
    enriched['_meta']['total_molecules'] = len(keep)
    
    with open('data/molecules/enriched_discoveries.json', 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)
    
    blocklist['blocked_formulas'] = sorted(list(blocked_set))
    blocklist['total'] = len(blocked_set)
    
    with open('data/molecules/blocklist.json', 'w', encoding='utf-8') as f:
        json.dump(blocklist, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Limpieza aplicada")
    print(f"  Enriched: {len(keep)} moléculas")
    print(f"  Blocklist: {len(blocked_set)} fórmulas")

if __name__ == "__main__":
    main()
