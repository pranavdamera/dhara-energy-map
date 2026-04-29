from sqlalchemy import create_engine

from .settings import settings

engine = create_engine(settings.database_url, future=True)
