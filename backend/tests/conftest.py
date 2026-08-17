import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-only-secret-that-is-at-least-32-characters")
os.environ.setdefault("ML_MODEL_DIR", ".test-models")

