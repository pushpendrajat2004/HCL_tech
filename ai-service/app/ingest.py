import json
from .providers import ingest, Unavailable
if __name__=='__main__':
    try: print(json.dumps(ingest(),indent=2))
    except Unavailable as exc: print(str(exc)); raise SystemExit(1)
