"""Construction d'un graphe d'attente processus -> processus."""

from ..domain.models import ProcessState
from .resource_manager import ResourceManager


def build_wait_for_graph(manager: ResourceManager) -> dict[str, set[str]]:
    graph = {pid: set() for pid in manager.processes}
    # Lecture cohérente des champs modifiés par les threads.
    with manager._lock:
        for process in manager.processes.values():
            if process.state is ProcessState.WAITING and process.waiting_for:
                owner = manager.owner_of(process.waiting_for)
                if owner is not None and owner != process.process_id:
                    graph[process.process_id].add(owner)
    return graph
