"""
NEXUS Configuration Module.
Loads environment variables, defines paths, and manages multi-account credentials.
"""

import os
from pathlib import Path
from typing import Any, List, Tuple, Dict, Optional
from dotenv import load_dotenv

# Define Project Paths
PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_DIR = PROJECT_ROOT / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Active Account Configuration
def parse_active_account(val: Any) -> int:
    if val is None:
        return 1
    val_str = str(val).strip().strip("\"'").strip()
    try:
        return int(val_str)
    except ValueError:
        return 1

ACTIVE_ACCOUNT = parse_active_account(os.getenv("ACTIVE_ACCOUNT", "1"))

# Multi-account Cookie Credentials
def get_accounts():
    """
    Returns a list of account credential tuples: (secure_1psid, secure_1psidts)
    Reads accounts from environment variables for backward compatibility.
    """
    accounts = []
    for idx in (1, 2, 3, 4, 5):
        psid = os.getenv(f"ACCOUNT{idx}_SECURE_1PSID", "").strip()
        psidts = os.getenv(f"ACCOUNT{idx}_SECURE_1PSIDTS", "").strip()
        if psid:
            accounts.append((psid, psidts))
    return accounts

def get_accounts_with_ids():
    """
    Returns a list of tuples: (account_number, secure_1psid, secure_1psidts)
    Preserves exact 1-based account ID (1 to 5) even if intermediate accounts are omitted.
    """
    accounts = []
    for idx in (1, 2, 3, 4, 5):
        psid = os.getenv(f"ACCOUNT{idx}_SECURE_1PSID", "").strip()
        psidts = os.getenv(f"ACCOUNT{idx}_SECURE_1PSIDTS", "").strip()
        if psid:
            accounts.append((idx, psid, psidts))
    return accounts

# Fallback & Third-party APIs
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

# System Defaults
DEFAULT_VOICE = "vi-VN-NamMinhNeural"
DEFAULT_TTS_RATE = "+18%"
ARGON_INIT_TIMEOUT = 30
PRO_FALLBACK_MODEL = os.getenv("PRO_FALLBACK_MODEL", "gemini-2.5-pro")
FLASH_FALLBACK_MODEL = os.getenv("FLASH_FALLBACK_MODEL", "gemini-2.5-flash")
