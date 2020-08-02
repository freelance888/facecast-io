class FacecastAPIError(Exception):
    ...


class AuthError(FacecastAPIError):
    ...


class DeviceNotFound(FacecastAPIError):
    ...


class DeviceNotCreated(FacecastAPIError):
    ...
