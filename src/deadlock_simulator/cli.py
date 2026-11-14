"""Interface en ligne de commande."""

import argparse
import logging

from .concurrency.runner import run_scenario_concurrently
from .logging_config import configure_logging
from .scenarios.examples import build_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulateur de situations d'interblocage")
    parser.add_argument("--scenario", choices=("safe", "deadlock"), default="safe")
    parser.add_argument("--timeout", type=float, default=5.0, help="Délai maximal en secondes")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout doit être strictement positif")

    configure_logging()
    manager, activities = build_scenario(args.scenario)
    try:
        run_scenario_concurrently(manager, activities, timeout=args.timeout)
    except (TimeoutError, RuntimeError) as exc:
        logging.getLogger(__name__).error("Échec contrôlé du scénario: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
