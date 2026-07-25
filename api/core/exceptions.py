import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(
    "urbanflow.exception_handler"
)


def register_exception_handlers(
    app: FastAPI,
) -> None:
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        logger.exception(
            "Database error: method=%s path=%s",
            request.method,
            request.url.path,
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "Veritabanı işlemi sırasında "
                    "beklenmeyen bir hata oluştu."
                )
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unexpected error: method=%s path=%s",
            request.method,
            request.url.path,
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": (
                    "Beklenmeyen bir sunucu hatası oluştu."
                )
            },
        )