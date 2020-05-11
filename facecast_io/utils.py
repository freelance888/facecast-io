import functools

from .core.errors import FacecastAPIError


def to_bool(bool_str):
    """Parse the string and return the boolean value encoded or raise an exception"""
    if isinstance(bool_str, str) and bool_str:
        if bool_str.lower() in ["true", "t", "1"]:
            return True
        elif bool_str.lower() in ["false", "f", "0"]:
            return False
    if isinstance(bool_str, int):
        return bool(bool_str)
    # if here we couldn't parse it
    raise ValueError("%s is no recognized as a boolean value" % bool_str)


def auth_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_authorized:
            raise FacecastAPIError("Need to authorize first")
        return func(self, *args, **kwargs)

    return wrapper
