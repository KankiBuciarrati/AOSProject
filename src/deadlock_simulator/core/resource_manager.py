"""État partagé et opérations atomiques sur les ressources."""

import logging
import threading

from ..domain.models import EventType, JournalEvent, Process, ProcessState, Resource

logger = logging.getLogger(__name__)


class ResourceManager:
    def __init__(self, resources: list[Resource], processes: list[Process]) -> None:
        self.resources = {r.resource_id: r for r in resources}
        self.processes = {p.process_id: p for p in processes}
        self._owner: dict[str, str] = {}
        self._lock = threading.RLock()
        self.events: list[JournalEvent] = []

    def request(self, process_id: str, resource_id: str) -> bool:
        with self._lock:
            process = self._process(process_id)
            if process.state is ProcessState.TERMINATED:
                raise RuntimeError(f"Le processus {process_id} est terminé")
            if resource_id not in self.resources:
                raise ValueError(f"Ressource inconnue: {resource_id}")
            self._record(EventType.REQUEST, process_id, resource_id)
            owner = self._owner.get(resource_id)
            if owner is None:
                self._owner[resource_id] = process_id
                process.held_resources.add(resource_id)
                process.waiting_for = None
                process.state = ProcessState.RUNNING
                self._record(EventType.ACQUIRE, process_id, resource_id)
                logger.info("Acquisition %s par %s", resource_id, process_id)
                return True
            if owner == process_id:
                raise RuntimeError(f"{process_id} détient déjà {resource_id}")
            process.waiting_for = resource_id
            process.state = ProcessState.WAITING
            logger.info("%s attend %s détenue par %s", process_id, resource_id, owner)
            return False

    def release_all(self, process_id: str) -> None:
        with self._lock:
            process = self._process(process_id)
            for resource_id in tuple(process.held_resources):
                self._owner.pop(resource_id, None)
                process.held_resources.remove(resource_id)
                self._record(EventType.RELEASE, process_id, resource_id)
                logger.info("Libération %s par %s", resource_id, process_id)
            process.waiting_for = None
            if process.state is ProcessState.WAITING:
                process.state = ProcessState.RUNNING

    def terminate(self, process_id: str, *, victim: bool = False) -> None:
        """Termine un processus et garantit la libération de ses ressources."""
        with self._lock:
            process = self._process(process_id)
            self.release_all(process_id)
            process.state = ProcessState.TERMINATED
            self.events.append(JournalEvent(EventType.TERMINATE, process_id))
            if victim:
                self.events.append(
                    JournalEvent(EventType.VICTIM, process_id, detail="victime de la récupération")
                )
            logger.info("Terminaison du processus %s", process_id)

    def owner_of(self, resource_id: str) -> str | None:
        with self._lock:
            if resource_id not in self.resources:
                raise ValueError(f"Ressource inconnue: {resource_id}")
            return self._owner.get(resource_id)

    def _process(self, process_id: str) -> Process:
        try:
            return self.processes[process_id]
        except KeyError as exc:
            raise ValueError(f"Processus inconnu: {process_id}") from exc

    def _record(self, kind: EventType, process_id: str, resource_id: str | None = None) -> None:
        self.events.append(JournalEvent(kind, process_id, resource_id))
