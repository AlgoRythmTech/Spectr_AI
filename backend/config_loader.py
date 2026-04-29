"""
Config Loader — per-firm (multi-tenant) configuration resolver.

Behavior:
  - FIRM_SHORT="" or unset  → running as spectr.in (multi-tenant SaaS)
                              → loads firms/_default/ overrides
                              → per-request tenant scoping from auth token

  - FIRM_SHORT="cam"         → running as cymllp.spectr.in (dedicated instance)
                              → loads firms/cam/ overrides
                              → all users on this instance are CAM users

Each firm directory can contain:
  - config.json           — tier limits, enabled features, branding
  - prompt_override.md    — appended to SPECTR_SYSTEM_PROMPT
  - branding.json         — colors, logo URL, fonts, email footers
  - playbook_overrides.py — firm-specific templates (their NDA, their SPA style)
  - citation_style.py     — firm-specific citation formatting
  - disclaimer.md         — footer text for generated documents

Fallback order for any key:
  firms/<firm>/  →  firms/_default/  →  backend default (hardcoded)
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("config_loader")

FIRM_SHORT = os.environ.get("FIRM_SHORT", "").strip().lower()

# firms/ lives at repo root (sibling to backend/), or inside /app/firms/ in Docker
_HERE = Path(__file__).parent
_candidates = [
    _HERE.parent / "firms",     # repo root layout: <repo>/firms, <repo>/backend/config_loader.py
    _HERE / "firms",             # Docker layout: /app/firms, /app/config_loader.py
    Path("/app/firms"),          # Absolute Docker path
]
FIRMS_DIR = next((p for p in _candidates if p.exists()), _candidates[0])

# Built-in firm catalog — add new firms here or via filesystem
_KNOWN_FIRMS = {
    "": "Multi-Tenant (spectr.in)",
    "_default": "Default",
    "algorythm": "Algorythm Technologies (Internal)",
    # Add client firms as they're onboarded:
    # "cam": "Cyril Amarchand Mangaldas",
    # "sam": "Shardul Amarchand Mangaldas",
    # "trilegal": "Trilegal",
}


class FirmConfig:
    """Loaded configuration for the current deployment."""

    def __init__(self, firm_short: str = FIRM_SHORT):
        self.firm_short = firm_short or "_default"
        self.is_dedicated = bool(firm_short)
        self.is_multi_tenant = not self.is_dedicated

        self.firm_name = _KNOWN_FIRMS.get(firm_short, "")
        self.firm_dir = FIRMS_DIR / self.firm_short
        self.default_dir = FIRMS_DIR / "_default"

        self._config = self._load_config()
        self._prompt_override = self._load_text("prompt_override.md")
        self._branding = self._load_json_file("branding.json")
        self._disclaimer = self._load_text("disclaimer.md")

        logger.info(f"Config loaded: firm={self.firm_short}, dedicated={self.is_dedicated}")

    def _load_config(self) -> dict:
        """Load config.json from firm dir, falling back to default."""
        config = self._load_json_file("config.json", default={})
        # Merge defaults if keys missing
        default_config = self._load_json_file_from(self.default_dir, "config.json", default={})
        for k, v in default_config.items():
            config.setdefault(k, v)
        return config

    def _load_json_file(self, name: str, default: Any = None) -> Any:
        """Try firm dir, then default dir."""
        firm_path = self.firm_dir / name
        if firm_path.exists():
            try:
                return json.loads(firm_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to parse {firm_path}: {e}")
        default_path = self.default_dir / name
        if default_path.exists():
            try:
                return json.loads(default_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to parse {default_path}: {e}")
        return default if default is not None else {}

    def _load_json_file_from(self, base: Path, name: str, default: Any = None) -> Any:
        path = base / name
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default if default is not None else {}

    def _load_text(self, name: str) -> str:
        """Load text file (markdown etc.), firm → default fallback."""
        for base in (self.firm_dir, self.default_dir):
            p = base / name
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8")
                except Exception:
                    pass
        return ""

    # --- PUBLIC API ---

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value with dotted-key support (e.g., 'limits.max_files')."""
        parts = key.split(".")
        val = self._config
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default
        return val

    @property
    def prompt_override(self) -> str:
        """Firm-specific prompt additions — appended to SPECTR_SYSTEM_PROMPT."""
        return self._prompt_override

    @property
    def branding(self) -> dict:
        """Branding dict: {logo_url, primary_color, font_stack, email_footer}."""
        return self._branding or self._load_json_file_from(self.default_dir, "branding.json", default={
            "app_name": "Spectr",
            "firm_name": "Spectr AI",
            "tagline": "AI Legal Intelligence for India",
            "primary_color": "#0A0A0A",
            "accent_color": "#D4AF37",
            "logo_url": "/static/spectr-logo.svg",
            "font_heading": "Plus Jakarta Sans",
            "font_body": "Inter",
        })

    @property
    def disclaimer(self) -> str:
        return self._disclaimer or "This analysis is AI-generated. Verify all citations and amounts before filing or relying on it."

    # --- LIMITS (tier-based for multi-tenant, fixed for dedicated) ---

    def tier_limit(self, user_tier: str, key: str, default: int = 0) -> int:
        """Get rate/usage limit for a user tier."""
        if self.is_dedicated:
            return self.get(f"limits.{key}", default)
        return self.get(f"tiers.{user_tier}.{key}", self.get(f"limits.{key}", default))

    def is_feature_enabled(self, feature: str) -> bool:
        enabled = self.get("features", {}).get(feature)
        return bool(enabled) if enabled is not None else True  # default enabled

    # --- DB SCOPING ---

    def mongo_tenant_filter(self, user_id: str) -> dict:
        """Returns Mongo filter to apply to every query for tenant isolation.

        Multi-tenant mode: scope by user_id (each user owns their data).
        Dedicated mode:   scope by firm_short (all users belong to one firm).
        """
        if self.is_dedicated:
            return {"firm": self.firm_short}
        return {"user_id": user_id}

    def inject_tenant(self, user_id: str, doc: dict) -> dict:
        """Stamp a document with tenant info before inserting."""
        doc = dict(doc)
        if self.is_dedicated:
            doc["firm"] = self.firm_short
        doc["user_id"] = user_id
        return doc


# Singleton
_config: Optional[FirmConfig] = None


def get_config() -> FirmConfig:
    global _config
    if _config is None:
        _config = FirmConfig()
    return _config


def reload_config():
    """For testing — force reload from disk."""
    global _config
    _config = FirmConfig()


# Convenience functions

def firm_short() -> str:
    return get_config().firm_short


def is_dedicated() -> bool:
    return get_config().is_dedicated


def get_prompt_override() -> str:
    return get_config().prompt_override


def get_branding() -> dict:
    return get_config().branding


def tenant_filter(user_id: str) -> dict:
    return get_config().mongo_tenant_filter(user_id)


def inject_tenant(user_id: str, doc: dict) -> dict:
    return get_config().inject_tenant(user_id, doc)


# Diagnostic
if __name__ == "__main__":
    c = get_config()
    print(f"Firm: {c.firm_short} ({c.firm_name})")
    print(f"Mode: {'DEDICATED' if c.is_dedicated else 'MULTI-TENANT'}")
    print(f"Branding: {c.branding}")
    print(f"Disclaimer: {c.disclaimer[:100]}...")
    print(f"Prompt override: {len(c.prompt_override)} chars")
