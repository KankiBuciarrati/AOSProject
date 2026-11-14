"""Configuration des traces horodatées."""

import logging
from pathlib import Path


def configure_logging(log_dir: Path = Path("logs")) -> None:
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers: list[logging.Handler] = [
            logging.FileHandler(log_dir / "simulation.log", encoding="utf-8"),
            logging.StreamHandler(),
        ]
    except OSError as exc:
        raise RuntimeError(f"Impossible de créer/ouvrir le journal: {exc}") from exc
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s pid=%(process)d thread=%(threadName)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
