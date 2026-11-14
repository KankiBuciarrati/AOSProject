"""Extension de prévention par ordre total des ressources."""


def respects_global_order(held_resources: set[str], requested_resource: str) -> bool:
    """Accepte une demande uniquement si elle respecte l'ordre lexical global."""
    return not held_resources or requested_resource > max(held_resources)
