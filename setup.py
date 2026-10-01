import asyncio
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from openai import AsyncOpenAI



# 2. Your crucial assertion check
assert os.environ.get('OPENAI_API_KEY'), 'Set OPENAI_API_KEY first'

client = AsyncOpenAI()

MODEL = 'gpt-4o-mini'
JUDGE_MODEL = 'gpt-4o'
TEMPERATURE = 0.0

# Cost rates ($ per token) — from W4 cost.py
RATES = {
    'gpt-4o-mini': {'in': 0.15 / 1_000_000, 'out': 0.60 / 1_000_000},
    'gpt-4o':      {'in': 2.50 / 1_000_000, 'out': 10.00 / 1_000_000},
}

print('Setup complete.')