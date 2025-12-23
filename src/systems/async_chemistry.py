"""
Async Chemistry Worker - Threading-based Molecular Detection
=============================================================
Ejecuta la detección molecular en un hilo separado para evitar bloquear
el loop principal de rendering.

Arquitectura:
- El loop principal encola snapshots de datos (atom_types, molecule_id, etc.)
- El worker procesa en segundo plano
- Los resultados se recogen de forma non-blocking
"""

import threading
import queue
import time
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from src.core.event_system import EventType, get_event_system


class AsyncChemistryWorker:
    """
    Worker thread para detección molecular asíncrona.
    
    Uso:
        worker = AsyncChemistryWorker()
        worker.start()
        
        # En cada frame:
        worker.submit_job(atom_types, molecule_id, num_enlaces, n_particles)
        
        # Verificar resultados (non-blocking):
        result = worker.get_result()
        if result:
            # Aplicar resultado...
            
        # Al cerrar:
        worker.stop()
    """
    
    def __init__(self, detector_func=None):
        """
        Args:
            detector_func: Función de detección a ejecutar. 
                          Si None, usa get_molecule_detector().detect_molecules_fast
        """
        self._input_queue = queue.Queue(maxsize=2)  # Máximo 2 jobs pendientes
        self._output_queue = queue.Queue(maxsize=4)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._detector_func = detector_func
        self._is_processing = False
        self._lock = threading.Lock()
        
        # Stats
        self.jobs_processed = 0
        self.avg_process_time_ms = 0.0
        self.last_process_time_ms = 0.0
    
    def start(self):
        """Inicia el worker thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # Ya está corriendo
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        print("[ASYNC CHEM] Worker iniciado.")
    
    def stop(self):
        """Detiene el worker thread de forma segura."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        print("[ASYNC CHEM] Worker detenido.")
    
    def submit_job(self, atom_types_np: np.ndarray, molecule_id_np: np.ndarray, 
                   num_enlaces_np: np.ndarray, pos_np: np.ndarray, 
                   n_particles: int, roi: Optional[Tuple[float, float, float, float]] = None) -> bool:
        """
        Encola un job de detección molecular.
        
        Args:
            atom_types_np: Array de tipos de átomo
            molecule_id_np: Array de IDs de molécula
            num_enlaces_np: Array de número de enlaces
            pos_np: Array de posiciones (X, Y) para ROI filtering
            n_particles: Número total de partículas
            roi: (min_x, min_y, max_x, max_y) area a procesar
            
        Returns:
            True si se encoló, False si la cola está llena (skip)
        """
        job_data = {
            'atom_types': atom_types_np.copy() if atom_types_np is not None else None,
            'molecule_id': molecule_id_np.copy() if molecule_id_np is not None else None,
            'num_enlaces': num_enlaces_np.copy() if num_enlaces_np is not None else None,
            'pos': pos_np.copy() if pos_np is not None else None,
            'n_particles': n_particles,
            'roi': roi,
            'timestamp': time.perf_counter()
        }
        
        try:
            self._input_queue.put_nowait(job_data)
            return True
        except queue.Full:
            return False  # Skip este frame, el worker está ocupado
    
    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene el resultado más reciente (non-blocking).
        
        Returns:
            Dict con stats y descubrimientos, o None si no hay resultados
        """
        result = None
        # Drenar cola para obtener el resultado más reciente
        while True:
            try:
                result = self._output_queue.get_nowait()
            except queue.Empty:
                break
        return result
    
    def is_busy(self) -> bool:
        """Retorna True si hay jobs pendientes o en proceso."""
        with self._lock:
            return self._is_processing or not self._input_queue.empty()
    
    def _worker_loop(self):
        """Loop principal del worker thread."""
        # Inicializar detector dentro del thread
        from src.systems.molecule_detector import get_molecule_detector
        detector = get_molecule_detector()
        
        while not self._stop_event.is_set():
            try:
                # Esperar job con timeout para poder verificar stop_event
                job = self._input_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            if job is None:
                continue
            
            with self._lock:
                self._is_processing = True
            
            try:
                start_time = time.perf_counter()
                
                # Ejecutar detección
                if job['atom_types'] is not None and job['molecule_id'] is not None:
                    # ROI Filtering: Pre-procesar partículas si hay ROI
                    atom_types = job['atom_types']
                    molecule_id = job['molecule_id']
                    num_enlaces = job['num_enlaces']
                    n_particles = job['n_particles']
                    
                    if job['roi'] is not None and job['pos'] is not None:
                        min_x, min_y, max_x, max_y = job['roi']
                        pos = job['pos']
                        # Filtrar: Poner num_enlaces a 0 para las que están fuera del ROI
                        # Esto engaña al detector para que las ignore
                        mask = (pos[:, 0] < min_x) | (pos[:, 0] > max_x) | \
                               (pos[:, 1] < min_y) | (pos[:, 1] > max_y)
                        num_enlaces[mask] = 0
                    
                    detector.detect_molecules_fast(
                        atom_types,
                        molecule_id,
                        num_enlaces,
                        n_particles
                    )
                
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                
                # Crear resultado
                result = {
                    'stats': detector.stats.copy(),
                    'discovered_count': len(detector.discovered_formulas),
                    'process_time_ms': elapsed_ms,
                    'job_timestamp': job['timestamp']
                }
                
                # Actualizar stats del worker
                self.jobs_processed += 1
                self.last_process_time_ms = elapsed_ms
                self.avg_process_time_ms = (
                    (self.avg_process_time_ms * (self.jobs_processed - 1) + elapsed_ms) 
                    / self.jobs_processed
                )
                
                # Encolar resultado
                try:
                    self._output_queue.put_nowait(result)
                except queue.Full:
                    pass  # Descartar resultado viejo
                    
            except Exception as e:
                print(f"[ASYNC CHEM] Error en worker: {e}")
            finally:
                with self._lock:
                    self._is_processing = False


# Singleton
_async_worker: Optional[AsyncChemistryWorker] = None


def get_async_chemistry_worker() -> AsyncChemistryWorker:
    """Obtiene la instancia singleton del worker."""
    global _async_worker
    if _async_worker is None:
        _async_worker = AsyncChemistryWorker()
    return _async_worker


def start_async_chemistry():
    """Inicia el worker (llamar al inicio del juego)."""
    get_async_chemistry_worker().start()


def stop_async_chemistry():
    """Detiene el worker (llamar al cerrar el juego)."""
    global _async_worker
    if _async_worker is not None:
        _async_worker.stop()
        _async_worker = None
