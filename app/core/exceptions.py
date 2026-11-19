from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for every error our services raise on purpose."""

    status_code: int = 400
    default_message: str = "Bad request"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    default_message = "Bad request"


class UnauthorizedError(AppError):
    status_code = 401
    default_message = "Not authenticated"


class ForbiddenError(AppError):
    status_code = 403
    default_message = "You do not have permission to do this"


class NotFoundError(AppError):
    status_code = 404
    default_message = "Not found"


class ConflictError(AppError):
    status_code = 409
    default_message = "Conflict with the current state of the resource"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the handler that turns AppError into a JSON response."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
            headers=headers,
        )