import functools

from .errors import FacecastAPIError


def auth_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_authorized:
            raise FacecastAPIError("Need to authorize first")
        return func(self, *args, **kwargs)

    return wrapper
