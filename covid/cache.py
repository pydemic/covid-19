import shelve
import uuid
from functools import wraps


def cache(path):
    """
    Simple decorator for caching picklable python results.
    """

    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            with shelve.open(path, "c") as db:
                ids = db.setdefault("ids", {})
                try:
                    call_id = ids[(args, tuple(kwargs.items()))]
                except KeyError:
                    pass
                else:
                    return db[call_id]

            value = func(*args, **kwargs)
            ref = ids[args, tuple(kwargs.items())] = str(uuid.uuid4())
            with shelve.open(path, "w") as db:
                db["ids"] = ids
                db[ref] = value
            return value

        return decorated

    return decorator
