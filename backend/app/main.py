from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes: int = 1_000_000) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                await send({
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [(b"content-type", b"application/json")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b'{"detail":"Request body too large"}',
                })
                return
            if not message.get("more_body", False):
                break

        body_bytes = bytes(body)
        first_read = True

        async def replay_body():
            nonlocal first_read
            if first_read:
                first_read = False
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return await receive()

        await self.app(scope, replay_body, send)


app = FastAPI(
    title="Social Circle Calendar API",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled and settings.environment != "production" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled and settings.environment != "production" else None,
)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1_000_000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path not in {"/docs", "/openapi.json"}:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router)
