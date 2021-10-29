# coding: utf-8

import time
import threading
import functools

import storage


def periodic(interval):
    def decorator(func):
        @functools.wraps(func)
        def loop(*args, **kwargs):
            while True:
                time.sleep(interval)
                func()

        @functools.wraps(func)
        def decorated(*args, **kwargs):
            thread = threading.Thread(
                target=loop,
                args=args,
                kwargs=kwargs,
                daemon=True
            )
            thread.start()
            return thread

        return decorated
    return decorator


@periodic(20 * 60)
def sync_to_remote():
    with storage.LOCK:
        storage.sync()
