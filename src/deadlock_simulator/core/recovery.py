"""Choix de victime et récupération."""

import logging
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


def choose_victim(cycle: list[str]) -> str:
    """Choisit le plus grand identifiant pour rendre la récupération reproductible.

    Cette politique de démonstration est simple et déterministe; une version
    ultérieure pourra comparer le coût de terminaison des processus.
    """
    members = cycle[:-1] if cycle and cycle[0] == cycle[-1] else cycle
    if not members:
        raise ValueError("Le cycle ne contient aucun processus")
    return sorted(members)[-1]


def recover(manager: ResourceManager, victim_id: str) -> None:
    manager.terminate(victim_id, victim=True)
    logger.warning("Processus victime %s terminé; ressources vérifiées libres", victim_id)
