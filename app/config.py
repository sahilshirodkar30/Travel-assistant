""" This module contains the configuration settings for the Travel Assistant project. """

from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")

    env:str ="dev"

    #authentication
    jwt_sceret:str = "dev-secret"
    jwt_ttl_minutes:int = 60
    internal_service_key:str="dev-internal-service-key"
    google_client_id:str="",
    ops_emails:str=""

    #infrastructure
    redis_url:str=""
    postgres_url:str=""

    #rate limiting / load shedding
    rate_limit_per_minute:int=20
    ip_rate_limit_per_minute:int=60
    max_concurrent_requests:int=50

    #pinecone / cache / freshness
    pinecone_api_key:str=""
    pinecone_index: str = ""
    embedding_model_name:str="text-embedding-3-small"
    cache_threshold:float=0.93
    cache_ttl_hours:int=24

    #models
    groq_api_key:str=""
    deepseek_api_key:str=""
    model_small:str=""
    model_medium:str=""
    model_large:str=""
    llm_timeout_seconds:int=20

    #agent limits
    request_budget_seconds:float=45
    max_agent_steps:int=6
    approval_threshold_inr:int = 5000

    #tools
    bookings_api_url:str=""
    bookings_api_key:str="dev"
    logfire_token:str=""



@lru_cache
def get_settings()->Settings:
    return Settings()
