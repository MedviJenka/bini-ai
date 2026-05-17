from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter
from starlette.middleware.base import BaseHTTPMiddleware
import traceback


app = FastAPI()


REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total number of requests",
    ["method", "endpoint"]
)

EXCEPTIONS = Counter(
    "app_exceptions_total",
    "Total number of unhandled exceptions",
    ["endpoint", "exception_type"]
)


class RequestCountMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path
        ).inc()
        return await call_next(request)


@app.exception_handler(Exception)
async def catch_all_exceptions(request: Request, exc: Exception):
    EXCEPTIONS.labels(
        endpoint=request.url.path,
        exception_type=type(exc).__name__
    ).inc()
    traceback.print_exc()
    return PlainTextResponse("Internal Server Error", status_code=500)


@app.get("/hello")
async def hello():
    return "Hello World!"


@app.get("/print_number")
async def print_number(number: int):
    return f"Number: {number}"


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, use_colors=True)
