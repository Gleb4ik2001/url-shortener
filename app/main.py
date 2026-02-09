import logging
import secrets
import string
import sqlite3

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse

from .settings import settings
from .models import ShortenRequest, ShortenResponse
from .db import init_db, connect, now_iso
from .logging_config import setup_logging


logger = logging.getLogger("url_shortener")

ALPHABET = string.ascii_letters + string.digits  # base62
CODE_LEN_DEFAULT = 7
MAX_RETRIES = 8


def generate_code(length: int = CODE_LEN_DEFAULT) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def create_app() -> FastAPI:
    setup_logging()
    init_db(settings.db_path)

    app = FastAPI(title="URL Shortener", version="0.1.0")

    @app.post(
        "/shorten",
        response_model=ShortenResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def shorten(payload: ShortenRequest) -> ShortenResponse:
        long_url = str(payload.url)
        requested_code = payload.custom_code

        with connect(settings.db_path) as conn:
            # 1) если пользователь просит custom_code — пробуем вставить, иначе 409
            if requested_code is not None:
                try:
                    conn.execute(
                        "INSERT INTO urls(code, long_url, created_at) VALUES(?, ?, ?)",
                        (requested_code, long_url, now_iso()),
                    )
                except sqlite3.IntegrityError:
                    logger.info("custom_code_conflict code=%s url=%s", requested_code, long_url)
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="custom_code already exists",
                    )
                code = requested_code
                logger.info("shorten_created code=%s url=%s", code, long_url)
                return ShortenResponse(
                    code=code,
                    short_url=f"{settings.base_url.rstrip('/')}/{code}",
                    long_url=long_url,
                )

            # 2) обычная генерация кода (с защитой от коллизий)
            for _ in range(MAX_RETRIES):
                code = generate_code()
                try:
                    conn.execute(
                        "INSERT INTO urls(code, long_url, created_at) VALUES(?, ?, ?)",
                        (code, long_url, now_iso()),
                    )
                    logger.info("shorten_created code=%s url=%s", code, long_url)
                    return ShortenResponse(
                        code=code,
                        short_url=f"{settings.base_url.rstrip('/')}/{code}",
                        long_url=long_url,
                    )
                except sqlite3.IntegrityError:
                    logger.warning("code_collision code=%s", code)
                    continue

        logger.error("shorten_failed url=%s", long_url)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to generate unique code",
        )

    @app.get("/{code}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    def redirect(code: str):
        with connect(settings.db_path) as conn:
            row = conn.execute("SELECT long_url FROM urls WHERE code = ?", (code,)).fetchone()

        if row is None:
            logger.info("redirect_not_found code=%s", code)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="code not found")

        long_url = row["long_url"]
        logger.info("redirect code=%s to=%s", code, long_url)
        return RedirectResponse(url=long_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return app


app = create_app()
