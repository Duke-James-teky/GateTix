from app.schemas.common import ErrorResponse

BAD_REQUEST = {
    400: {"model": ErrorResponse, "description": "The request breaks a business rule"}
}
UNAUTHORIZED = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"}
}
FORBIDDEN = {
    403: {"model": ErrorResponse, "description": "Your role or ownership does not allow this"}
}
NOT_FOUND = {
    404: {"model": ErrorResponse, "description": "The resource does not exist"}
}
CONFLICT = {
    409: {"model": ErrorResponse, "description": "Conflicts with the current state"}
}