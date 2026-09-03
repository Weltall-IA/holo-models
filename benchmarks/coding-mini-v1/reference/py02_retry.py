from functools import wraps


def retry(max_attempts, exceptions=(Exception,)):
    if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or max_attempts <= 0:
        raise ValueError("max_attempts must be an integer > 0")

    if isinstance(exceptions, type) and issubclass(exceptions, BaseException):
        exc_types = (exceptions,)
    elif isinstance(exceptions, tuple) and all(isinstance(e, type) and issubclass(e, BaseException) for e in exceptions):
        exc_types = exceptions
    else:
        raise ValueError("exceptions must be an exception class or tuple of exception classes")

    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            attempts = 0
            while True:
                attempts += 1
                try:
                    return fn(*args, **kwargs)
                except exc_types as exc:
                    if attempts >= max_attempts:
                        raise exc
        return wrapped
    return decorate
