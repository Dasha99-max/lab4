import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .logging_config import event
from .routers import auth, resources

app = FastAPI(title="Lab 4: регистрация и дискреционная модель доступа")
app.include_router(auth.router)
app.include_router(resources.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"] if p != "body")
        msg = err["msg"].removeprefix("Value error, ")
        if err["type"] == "missing":
            msg = "Обязательное поле не заполнено"
        elif err["type"] in ("string_too_short", "string_too_long", "string_type"):
            msg = "Недопустимое значение поля (длина или тип)"
        errors.append({"field": field, "message": msg})
    event(logging.INFO, "validation_error", path=request.url.path, fields=[e["field"] for e in errors])
    return JSONResponse(
        status_code=422, content={"detail": "; ".join(e["message"] for e in errors), "errors": errors}
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    log = logging.getLogger("app")
    log.error("unhandled_error", extra={"fields": {"path": request.url.path}}, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


@app.get("/api/health")
def health():
    return {"status": "ok"}
