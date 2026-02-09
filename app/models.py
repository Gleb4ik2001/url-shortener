from pydantic import BaseModel, HttpUrl, Field


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Опционально: задать собственный код",
    )


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    long_url: str
