"""Configurations for the project."""

# %% IMPORTS

import logging
import os

# %% CONFIGS

# %% Authentication

AUTHENTICATION_CLIENT_ID = os.environ["AUTHENTICATION_CLIENT_ID"]
AUTHENTICATION_CLIENT_SECRET = os.environ["AUTHENTICATION_CLIENT_SECRET"]

# %% Concurrent

CONCURRENT_TRANSLATION_WORKERS = int(os.getenv("CONCURRENT_TRANSLATION_WORKERS", "10"))
CONCURRENT_TRANSLATIONS_PER_WORKER = int(os.getenv("CONCURRENT_TRANSLATIONS_PER_WORKER", "20"))

# %% Logging

LOGGING_LEVEL = getattr(logging, os.getenv("LOGGING_LEVEL", "INFO").upper())
LOGGING_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# %% Models

MODEL_NAME_AGENT = os.getenv("MODEL_NAME_AGENT", "gemini-2.5-flash")
MODEL_NAME_TRANSLATION = os.getenv("MODEL_NAME_TRANSLATION", "gemini-2.5-flash")

# %% Projects

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
PROJECT_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

# %% Tokens

TOKEN_CACHE_KEY = os.getenv("TOKEN_CACHE_KEY", "user:slides_translator_token")
