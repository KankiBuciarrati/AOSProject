"""Exécution concurrente avec annulation coopérative et nettoyage garanti."""

import logging
import threading
import time
from collections.abc import Callable

from ..core.detector import find_cycles
from ..core.recovery import choose_victim, recover
from ..core.resource_manager import ResourceManager
from ..core.wait_for_graph import build_wait_for_graph
from ..domain.models import ProcessState

logger = logging.getLogger(__name__)
Activity = Callable[[ResourceManager, threading.Event], None]
SHUTDOWN_GRACE_SECONDS = 1.0


def _terminate_if_needed(manager: ResourceManager, process_id: str) -> None:
    if manager.processes[process_id].state is not ProcessState.TERMINATED:
        manager.terminate(process_id)


def _request_stop_and_join(
    stop: threading.Event, threads: list[threading.Thread], grace: float
) -> list[str]:
    """Demande l'arrêt puis attend les activités coopératives jusqu'au délai."""
    stop.set()
    for thread in threads:
        if thread.ident is not None:
            thread.join(timeout=grace)
    return [thread.name for thread in threads if thread.is_alive()]


def run_scenario_concurrently(
    manager: ResourceManager,
    activities: dict[str, Activity],
    timeout: float = 5.0,
) -> None:
    if timeout <= 0:
        raise ValueError("Le délai doit être strictement positif")
    unknown = set(activities) - set(manager.processes)
    if unknown:
        raise ValueError(f"Processus inconnu dans les activités: {sorted(unknown)}")

    stop = threading.Event()
    errors: list[tuple[str, Exception]] = []

    def run(process_id: str, activity: Activity) -> None:
        try:
            activity(manager, stop)
        except Exception as exc:
            errors.append((process_id, exc))
            logger.exception("Activité %s terminée en erreur", process_id)
            stop.set()
        finally:
            _terminate_if_needed(manager, process_id)

    threads: list[threading.Thread] = []
    try:
        for process_id, activity in activities.items():
            thread = threading.Thread(
                target=run,
                args=(process_id, activity),
                name=f"worker-{process_id}",
            )
            thread.start()
            threads.append(thread)
    except RuntimeError as exc:
        alive = _request_stop_and_join(stop, threads, SHUTDOWN_GRACE_SECONDS)
        for process_id in activities:
            if not any(thread.name == f"worker-{process_id}" for thread in threads):
                _terminate_if_needed(manager, process_id)
        detail = f"; threads encore actifs: {alive}" if alive else ""
        raise RuntimeError(f"Impossible de créer/démarrer un thread de simulation{detail}") from exc

    deadline = time.monotonic() + timeout
    try:
        while any(thread.is_alive() for thread in threads) and time.monotonic() < deadline:
            cycles = find_cycles(build_wait_for_graph(manager))
            if cycles:
                victim = choose_victim(cycles[0])
                logger.warning("Cycle détecté %s; récupération par terminaison de %s", cycles[0], victim)
                recover(manager, victim)
                stop.set()
            time.sleep(0.01)
    except KeyboardInterrupt:
        logger.warning("Interruption utilisateur; arrêt coopératif demandé")
        alive = _request_stop_and_join(stop, threads, SHUTDOWN_GRACE_SECONDS)
        if not alive:
            for process_id in activities:
                _terminate_if_needed(manager, process_id)
        else:
            logger.error("Arrêt incomplet; threads encore actifs: %s", alive)
        raise

    still_running = [thread for thread in threads if thread.is_alive()]
    if still_running:
        alive = _request_stop_and_join(stop, threads, SHUTDOWN_GRACE_SECONDS)
        if alive:
            raise TimeoutError(
                "Délai dépassé; les activités n'ont pas toutes répondu à l'arrêt coopératif: "
                + ", ".join(alive)
            )
        for process_id in activities:
            _terminate_if_needed(manager, process_id)
        raise TimeoutError("Délai dépassé; arrêt coopératif effectué et ressources libérées")

    for thread in threads:
        thread.join()
    if errors:
        raise RuntimeError(f"L'activité {errors[0][0]} a échoué") from errors[0][1]

    # Invariant de sortie: aucun processus n'est propriétaire d'une ressource.
    leaked = [rid for rid in manager.resources if manager.owner_of(rid) is not None]
    if leaked:
        raise RuntimeError(f"Ressources non libérées à la fin: {leaked}")
