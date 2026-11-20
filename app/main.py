from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.core.exceptions import register_exception_handlers
from app.routes import admin, auth, events, health, organisers, tiers

API_PREFIX = "/api/v1"

app = FastAPI(
    title="GateTix API",
    description=(
        "Backend API for an event ticketing platform. Organisers create events with "
        "ticket tiers, attendees reserve and buy tickets, and staff check tickets in "
        "at the venue.\n\n"
        "**To use protected endpoints:** register, log in, click **Authorize**, "
        "and paste the access token."
    ),
    version="1.0.0",
)

register_exception_handlers(app)

app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(organisers.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(tiers.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")