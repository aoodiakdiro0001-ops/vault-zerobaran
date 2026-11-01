"""
Vault-ZeroBaran — Central configuration loader.

Loads environment variables from .env, validates them with Pydantic,
and exposes a single `settings` instance used by every module.
"""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve project root (3 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Strongly-typed configuration for the entire Vault-ZeroBaran system."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Gemini ---
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_embedding_model: str = Field(default="text-embedding-004", alias="GEMINI_EMBEDDING_MODEL")
    gemini_chat_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_CHAT_MODEL")

    # --- Groq (optional) ---
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_chat_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_CHAT_MODEL")

    # --- Supabase ---
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")
    supabase_db_url: str = Field(default="", alias="SUPABASE_DB_URL")

    # --- Telegram ---
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_admin_chat_id: str = Field(default="", alias="TELEGRAM_ADMIN_CHAT_ID")

    # --- Vault behavior ---
    vault_data_dir: str = Field(default="./data/uploads", alias="VAULT_DATA_DIR")
    vault_chunk_size: int = Field(default=1000, alias="VAULT_CHUNK_SIZE")
    vault_chunk_overlap: int = Field(default=200, alias="VAULT_CHUNK_OVERLAP")
    vault_top_k: int = Field(default=5, alias="VAULT_TOP_K")
    vault_max_tokens: int = Field(default=2048, alias="VAULT_MAX_TOKENS")
    vault_language: str = Field(default="ar", alias="VAULT_LANGUAGE")
    vault_temperature: float = Field(default=0.2, alias="VAULT_TEMPERATURE")

    # --- Owner / copyright ---
    owner_name: str = Field(default="Vault-ZeroBaran Author", alias="OWNER_NAME")
    owner_email: str = Field(default="", alias="OWNER_EMAIL")
    owner_handle: str = Field(default="", alias="OWNER_HANDLE")

    @field_validator("vault_language")
    @classmethod
    def _validate_lang(cls, v: str) -> str:
        if v not in {"ar", "en", "auto"}:
            raise ValueError("VAULT_LANGUAGE must be one of: ar, en, auto")
        return v

    # --- Convenience derived properties ---
    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def data_dir(self) -> Path:
        p = PROJECT_ROOT / self.vault_data_dir if not os.path.isabs(self.vault_data_dir) else Path(self.vault_data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key and "your_" not in self.gemini_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key and "your_" not in self.groq_api_key)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key
                    and "your_" not in self.supabase_url)

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and "your_" not in self.telegram_bot_token)

    def ownership_block(self) -> str:
        """A short attribution string shown in UI / bot responses."""
        handle = f" (@{self.owner_handle})" if self.owner_handle and "ضع" not in self.owner_handle else ""
        email = f" — {self.owner_email}" if self.owner_email and "ضع" not in self.owner_email else ""
        name = self.owner_name if "ضع" not in self.owner_name else "Vault-ZeroBaran"
        return f"Vault-ZeroBaran © {name}{handle}{email}"


# Singleton
settings = Settings()
