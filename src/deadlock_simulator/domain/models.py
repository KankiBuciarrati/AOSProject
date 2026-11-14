"""Modèles de données du simulateur."""

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Resource:
    """Ressource modélisée avec une seule instance dans la version initiale."""

    resource_id: str
    name: str


class ProcessState(str, Enum):
    """Codes d'état observables sous Linux (R, S, D, T, Z, I)."""

    RUNNING = "R"  # En exécution ou prêt dans une file d'exécution.
    READY = "R"  # Sous-état du code R; Linux ne le distingue pas de RUNNING.
    INTERRUPTIBLE_SLEEP = "S"  # Attente pouvant être interrompue par un signal.
    WAITING = "S"  # Attente de ressource, modélisée comme interruptible.
    UNINTERRUPTIBLE_SLEEP = "D"  # Attente noyau, généralement liée à une E/S.
    STOPPED = "T"  # Arrêté ou suivi par un débogueur.
    ZOMBIE = "Z"  # Terminé, en attente de récupération par son parent.
    IDLE = "I"  # Thread noyau inactif.
    TERMINATED = "Z"  # Alias métier: terminaison non encore récupérée.


@dataclass
class Process:
    process_id: str
    name: str
    held_resources: set[str] = field(default_factory=set)
    waiting_for: str | None = None
    state: ProcessState = ProcessState.READY


class EventType(str, Enum):
    REQUEST = "request"
    ACQUIRE = "acquire"
    RELEASE = "release"
    TERMINATE = "terminate"
    VICTIM = "victim"


@dataclass(frozen=True)
class JournalEvent:
    event_type: EventType
    process_id: str
    resource_id: str | None = None
    detail: str = ""
