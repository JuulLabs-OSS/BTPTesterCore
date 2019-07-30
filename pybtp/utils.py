from concurrent.futures import wait


def wait_futures(futures, timeout=None):
    doneandnotdonefutures = wait(futures, timeout=timeout)
    if len(doneandnotdonefutures.not_done) != 0:
        raise TimeoutError

    return doneandnotdonefutures
