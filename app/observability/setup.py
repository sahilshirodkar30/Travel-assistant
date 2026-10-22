"""Observability: Logfire traces for FastAPI, httpx (tool/LLM calls), plus custom spans in the pipeline."""
import logfire
from app.config import get_settings


def setup(app=None):
    s = get_settings()
    logfire.configure(service_name="goa-travel-assistant", environment=s.env,
                      token=s.logfire_token or None, send_to_logfire="if-token-present")
    logfire.instrument_httpx()
    if app is not None:
        logfire.instrument_fastapi(app)
