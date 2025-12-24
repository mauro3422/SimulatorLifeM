#!/usr/bin/env python
"""
Script para analizar las moléculas emergentes restantes.
Verifica si son químicamente plausibles o física rota.
"""
import json
import re

def parse_formula(formula):
    """Extrae conteos de átomos de una fórmula."""
    atoms = {}
    for match in re.finditer(r'([A-Z][a-z]?)(\d+)', formula):
        element = match.group(1)
        count = int(match.group(2))
        atoms[element] = count
    return atoms

def check_valence(atoms):
    """Verifica si la valencia es plausible."""
    # Valencias típicas
    valences = {'C': 4, 'H': 1, 'O': 2, 'N': 3, 'S': 2, 'P': 3, 'Si': 4}
    
    # Calcular electrones de valencia disponibles
    total_bonds_needed = 0
    h_bonds = atoms.get('H', 0) * 1  # H siempre necesita 1
    
    for elem, count in atoms.items():
        if elem != 'H':
            total_bonds_needed += valences.get(elem, 4) * count
    
    # H debería satisfacer parte de los enlaces
    # Fórmula simplificada: sum(valence*count) debe ser par (enlaces)
    total = sum(valences.get(e, 4) * c for e, c in atoms.items())
    
    return total % 2 == 0, total

def analyze_emergent():
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=== ANÁLISIS DE MOLÉCULAS EMERGENTES ===\n")
    
    valid = []
    suspicious = []
    broken = []
    
    for formula, mol in data['molecules'].items():
        name = mol['identity']['names']['es']
        times = mol['gameplay'].get('times_synthesized', 0)
        significant = mol['status'].get('is_significant', False)
        
        atoms = parse_formula(formula)
        is_valid, total_valence = check_valence(atoms)
        
        # Reglas de validación
        c = atoms.get('C', 0)
        h = atoms.get('H', 0)
        o = atoms.get('O', 0)
        n = atoms.get('N', 0)
        s = atoms.get('S', 0)
        p = atoms.get('P', 0)
        si = atoms.get('Si', 0)
        
        issues = []
        
        # Demasiado pocas H para los carbonos
        if c > 0 and h < c:
            issues.append(f"H/C muy bajo ({h}/{c})")
        
        # Demasiados átomos pesados sin H
        heavy = c + n + o + s + p + si
        if heavy > 3 and h < 2:
            issues.append(f"Muy poca H para {heavy} átomos pesados")
        
        # Múltiples P o S sin estabilización
        if p >= 2 and h < p * 2:
            issues.append(f"P{p} sin suficiente H")
        if s >= 2 and h < s * 2:
            issues.append(f"S{s} sin suficiente H")
        
        # Valencia impar (imposible para molécula estable)
        if not is_valid:
            issues.append("Valencia impar")
        
        # Solo apareció 1 vez - sospechoso
        if times == 1:
            issues.append("Solo 1 síntesis")
        
        # Clasificar
        if len(issues) >= 2:
            broken.append((formula, name, times, issues))
        elif len(issues) == 1:
            suspicious.append((formula, name, times, issues))
        else:
            valid.append((formula, name, times, significant))
    
    print(f"✓ VÁLIDAS ({len(valid)}):")
    for f, n, t, sig in valid:
        mark = "★" if sig else " "
        print(f"  {mark} {f}: {n} (×{t})")
    
    print(f"\n⚠ SOSPECHOSAS ({len(suspicious)}):")
    for f, n, t, issues in suspicious:
        print(f"  {f}: {n} (×{t}) - {', '.join(issues)}")
    
    print(f"\n✗ FÍSICA ROTA ({len(broken)}):")
    for f, n, t, issues in broken:
        print(f"  {f}: {n} (×{t}) - {', '.join(issues)}")
    
    return valid, suspicious, broken

if __name__ == "__main__":
    analyze_emergent()
