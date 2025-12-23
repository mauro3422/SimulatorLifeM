#!/usr/bin/env python3
"""
Monitor de Performance - LifeSimulator
======================================
Herramienta para visualizar métricas de rendimiento en terminal.

Uso:
    python monitor.py              # Ver último benchmark
    python monitor.py --live       # Monitorear en tiempo real
    python monitor.py --all        # Mostrar todos los logs
    python monitor.py --export X   # Exportar a JSON
"""

import argparse
import json
import os
import re
import time
from pathlib import Path
from datetime import datetime

RESULTS_DIR = Path(__file__).parent / "results"
LOGS_DIR = Path(__file__).parent.parent / "logs"

# Colores ANSI
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

def parse_log_file(filepath: Path) -> dict:
    """Parsea un archivo de log y extrae métricas."""
    metrics = {
        "file": filepath.name,
        "fps": [],
        "physics_ms": [],
        "datatx_ms": [],
        "n_visible": [],
        "n_simulated": []
    }
    
    if not filepath.exists():
        return metrics
    
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    
    # Patrones de búsqueda
    fps_pattern = r"FPS:\s*([\d.]+)"
    physics_pattern = r"Physics:\s*([\d.]+)ms"
    datatx_pattern = r"DataTx:\s*([\d.]+)ms"
    visible_pattern = r"n_visible.*?(\d+)"
    simulated_pattern = r"n_simulated.*?(\d+)"
    
    for match in re.finditer(fps_pattern, content):
        metrics["fps"].append(float(match.group(1)))
    for match in re.finditer(physics_pattern, content):
        metrics["physics_ms"].append(float(match.group(1)))
    for match in re.finditer(datatx_pattern, content):
        metrics["datatx_ms"].append(float(match.group(1)))
    for match in re.finditer(visible_pattern, content):
        metrics["n_visible"].append(int(match.group(1)))
    for match in re.finditer(simulated_pattern, content):
        metrics["n_simulated"].append(int(match.group(1)))
    
    return metrics

def calculate_summary(metrics: dict) -> dict:
    """Calcula resumen estadístico de métricas."""
    summary = {}
    for key in ["fps", "physics_ms", "datatx_ms", "n_visible", "n_simulated"]:
        values = metrics.get(key, [])
        if values:
            summary[key] = {
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values)
            }
    return summary

def print_header():
    """Imprime encabezado del monitor."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  📊 LifeSimulator Performance Monitor{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

def print_metrics(summary: dict, title: str = "Resumen"):
    """Imprime métricas formateadas."""
    print(f"{BOLD}{title}{RESET}")
    print("-" * 40)
    
    if "fps" in summary:
        fps = summary["fps"]
        color = GREEN if fps["avg"] > 60 else (YELLOW if fps["avg"] > 30 else RED)
        print(f"  FPS:        {color}{fps['avg']:.1f}{RESET} (min: {fps['min']:.1f}, max: {fps['max']:.1f})")
    
    if "physics_ms" in summary:
        phys = summary["physics_ms"]
        color = GREEN if phys["avg"] < 5 else (YELLOW if phys["avg"] < 10 else RED)
        print(f"  Physics:    {color}{phys['avg']:.2f}ms{RESET} (max: {phys['max']:.2f}ms)")
    
    if "datatx_ms" in summary:
        dtx = summary["datatx_ms"]
        color = GREEN if dtx["avg"] < 1 else (YELLOW if dtx["avg"] < 3 else RED)
        print(f"  DataTx:     {color}{dtx['avg']:.2f}ms{RESET} (max: {dtx['max']:.2f}ms)")
    
    if "n_visible" in summary:
        vis = summary["n_visible"]
        print(f"  Visible:    {vis['avg']:.0f} partículas (max: {vis['max']})")
    
    if "n_simulated" in summary:
        sim = summary["n_simulated"]
        print(f"  Simulated:  {sim['avg']:.0f} partículas (max: {sim['max']})")
    
    print()

def scan_all_logs() -> list:
    """Escanea todos los logs disponibles."""
    all_metrics = []
    
    # Logs en results/
    if RESULTS_DIR.exists():
        for log_file in RESULTS_DIR.glob("*.log"):
            metrics = parse_log_file(log_file)
            if any(metrics[k] for k in ["fps", "physics_ms"]):
                all_metrics.append(metrics)
    
    # Logs en logs/
    if LOGS_DIR.exists():
        for log_file in LOGS_DIR.glob("*.log"):
            metrics = parse_log_file(log_file)
            if any(metrics[k] for k in ["fps", "physics_ms"]):
                all_metrics.append(metrics)
    
    return all_metrics

def monitor_live():
    """Monitorea en tiempo real (placeholder para integración futura)."""
    print(f"{YELLOW}⚠ Modo live no implementado aún.{RESET}")
    print("Para monitoreo en tiempo real, ejecuta la simulación con:")
    print(f"  {CYAN}python main.py{RESET}")
    print("\nLos logs se actualizarán en benchmarks/results/")

def export_json(all_metrics: list, output_path: str):
    """Exporta métricas a JSON."""
    export_data = {
        "generated": datetime.now().isoformat(),
        "logs": []
    }
    
    for metrics in all_metrics:
        summary = calculate_summary(metrics)
        export_data["logs"].append({
            "file": metrics["file"],
            "summary": summary
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2)
    
    print(f"{GREEN}✓ Exportado a {output_path}{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Monitor de Performance LifeSimulator")
    parser.add_argument("--live", action="store_true", help="Monitoreo en tiempo real")
    parser.add_argument("--all", action="store_true", help="Mostrar todos los logs")
    parser.add_argument("--export", type=str, help="Exportar a archivo JSON")
    args = parser.parse_args()
    
    print_header()
    
    if args.live:
        monitor_live()
        return
    
    all_metrics = scan_all_logs()
    
    if not all_metrics:
        print(f"{YELLOW}No se encontraron logs de benchmark.{RESET}")
        print(f"Ejecuta un benchmark primero:")
        print(f"  {CYAN}python benchmarks/benchmark_gpu.py{RESET}")
        return
    
    if args.export:
        export_json(all_metrics, args.export)
        return
    
    # Mostrar resumen
    for metrics in all_metrics:
        summary = calculate_summary(metrics)
        if summary:
            print_metrics(summary, f"📁 {metrics['file']}")
    
    # Resumen global
    print(f"{BOLD}{'='*40}{RESET}")
    print(f"{GREEN}Total logs analizados: {len(all_metrics)}{RESET}")

if __name__ == "__main__":
    main()
