import time
from contextlib import contextmanager
from functools import wraps
from src.common.logger import logger

@contextmanager
def track_execution_time(task_name: str):
    """
    Context manager to measure and log the execution duration of a code block.
    """
    start_time = time.perf_counter()
    logger.info(f"⏱️ Started: {task_name}")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        minutes, seconds = divmod(elapsed, 60)
        if minutes > 0:
            logger.info(f"✅ Completed: {task_name} in {int(minutes)}m {seconds:.2f}s")
        else:
            logger.info(f"✅ Completed: {task_name} in {seconds:.2f}s")

def timeit(func):
    """
    Decorator to automatically measure and log the execution time of any function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with track_execution_time(func.__name__):
            return func(*args, **kwargs)
    return wrapper
