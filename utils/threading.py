from concurrent.futures import ThreadPoolExecutor


def run_parallel(func, iterable, workers=8):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(func, iterable))
