import logging
import sys
from pathlib import Path

import uvicorn
import yaml

logger = logging.getLogger(__name__)


def load_config(path: str | None = None) -> dict:
    if path is None:
        path = str(Path(__file__).resolve().parent.parent.parent / "config.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    config = load_config()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    server_cfg = config.get("server", {"host": "0.0.0.0", "port": 8080})

    logger.info("BayesianSprinkler server starting on %s:%d",
                server_cfg["host"], server_cfg["port"])
    logger.info("Plants: %s", ", ".join(config["plants"].keys()))
    logger.info("ESP: %s | Inference interval: %ds",
                config["esp"]["base_url"], config["esp"]["poll_interval"])

    from bayesian_sprinkler.api import create_app
    app = create_app(config)
    uvicorn.run(app, host=server_cfg["host"], port=server_cfg["port"],
                log_level="info")


if __name__ == "__main__":
    main()
