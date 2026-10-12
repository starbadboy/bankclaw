import os

# Token signing refuses its dev default when MONGODB_URL is set (a local .env sets it); give tests a fixed secret.
os.environ.setdefault("AUTH_TOKEN_SECRET", "test-only-auth-secret")
