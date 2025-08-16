# config/settings/__init__.py
import os

ENV = os.getenv("APP_ENV", "dev").lower()
if ENV == "prod":
    from .prod import *
else:
    from .dev import *
