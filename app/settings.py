from dataclasses import dataclass
from decouple import config


@dataclass(frozen=True)
class Settings:
    base_url: str = config("BASE_URL", cast = str , default = "http://localhost:8000")
    db_path: str = config("DB_PATH", cast = str, default =  "urls.sqlite3")


settings = Settings()
