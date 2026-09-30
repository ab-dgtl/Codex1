import logging
import time

from .config import Settings
from .db import claim, finish
from .providers import analyze, predict

log = logging.getLogger(__name__)


def process_one(settings):
    run = claim(settings.database_path)
    if not run:
        return False
    try:
        import json
        spec = json.loads(run["spec"])
        result = predict(spec, settings)
        if spec.get("analyze"):
            result["analysis"] = analyze(spec, result, settings)
        finish(settings.database_path, run["id"], result=result)
    except Exception as exc:
        # Never persist exception text: upstream URLs/messages can contain secrets.
        log.warning("Run %s failed: %s", run["id"], type(exc).__name__)
        finish(settings.database_path, run["id"], error=type(exc).__name__)
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    while True:
        if not process_one(settings):
            time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
