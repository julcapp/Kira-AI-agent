import os
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["APP_API_KEY"] = "test-key"
from sqlalchemy.pool import StaticPool
from app.db import Base, engine
import pytest

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
