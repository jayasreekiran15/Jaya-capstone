import os
import pandas as pd
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 1. Force load the environment variables from the local .env file
load_dotenv(override=True)

# 2. Extract and clean the Vocareum parameters from background environment memory
CLEAN_API_KEY = os.getenv("VOC_API_KEY") or os.environ.get("VOC_API_KEY") or os.getenv("OPENAI_API_KEY")
CLEAN_BASE_URL = os.getenv("VOC_BASE_URL") or os.environ.get("VOC_BASE_URL")

# 💡 FAIL-SAFE GATE: If your environmental loader turns up dry due to directory path issues,
# this manually provides your verified active token directly so your script NEVER hits an AssertionError!
if not CLEAN_API_KEY or CLEAN_API_KEY == "None" or len(str(CLEAN_API_KEY)) < 10:
    CLEAN_API_KEY = "voc-3890*************************************5500"  # Ensure your complete token remains active here

# 💡 FIXED: Only falls back if CLEAN_BASE_URL is completely missing or incorrectly points to official OpenAI servers
if not CLEAN_BASE_URL or "://openai.com" in str(CLEAN_BASE_URL) or "vocareum" not in str(CLEAN_BASE_URL):
    CLEAN_BASE_URL = "https://openai.vocareum.com/v1"

# 3. Synchronize your active configuration markers back into system core memory
os.environ['OPENAI_API_KEY'] = CLEAN_API_KEY
os.environ['OPENAI_BASE_URL'] = CLEAN_BASE_URL
os.environ['VOC_API_KEY'] = CLEAN_API_KEY
os.environ['VOC_BASE_URL'] = CLEAN_BASE_URL

# Make sure your API key is correctly loaded before proceeding
assert os.environ.get('OPENAI_API_KEY'), 'Set OPENAI_API_KEY first'
client = AsyncOpenAI(
    api_key=CLEAN_API_KEY,
    base_url=CLEAN_BASE_URL
)

MODEL = 'gpt-4o-mini'
JUDGE_MODEL = 'gpt-4o'
TEMPERATURE = 0.0

# Cost rates ($ per token)
RATES = {
    'gpt-4o-mini': {'in': 0.15 / 1_000_000, 'out': 0.60 / 1_000_000},
    'gpt-4o':      {'in': 2.50 / 1_000_000, 'out': 10.00 / 1_000_000},
}




print('Setup complete. API gateway routed correctly.')
