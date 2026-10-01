import os
from dotenv import load_dotenv

load_dotenv(override=True)

print("--- ENV FILE DIAGNOSTIC ---")
print(f"1. API Key Found: {os.environ.get('OPENAI_API_KEY') is not None}")
print(f"2. Raw Key starts with: {str(os.environ.get('OPENAI_API_KEY'))[:10]}...")
print(f"3. Base URL Found: {os.environ.get('OPENAI_BASE_URL')}")
print("---------------------------")
cot_cost = 0.00165
few_shot_cost = 0.00047
structured_cost = 0.00036
zero_shot_cost = 0.00037

print(f"cot/structured cost ratio: {cot_cost / structured_cost:.2f}")
print(f"few_shot/structured cost ratio: {few_shot_cost / structured_cost:.2f}")
print(f"zero_shot/structured cost ratio: {zero_shot_cost / structured_cost:.2f}")
