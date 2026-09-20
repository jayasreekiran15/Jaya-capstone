
import asyncio
from asyncio import tasks
from http import client
import os
import time
import sys
import csv
from openai import AsyncOpenAI
from openai import BaseModel, OpenAI
from dotenv import load_dotenv 
import openai
import pandas as pd
from Load_data import  getdata
import json
from setup import MODEL, JUDGE_MODEL, TEMPERATURE, RATES
from pydantic import BaseModel

# 1. Tell Python to look one folder up (the root folder) for modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Defined pydantic model to structure the output of each job extraction result

class JobExtractionResult(BaseModel):
    job_id: str 
    strategy_name: str
    prompt_sent: str
    raw_response: str
    total_cost_usd:float
    latency_seconds:float

# Load environment variables from a .env file (if present)
load_dotenv()

#Getting the data from Load_data.py
snippets, golden = getdata()
results_df = pd.DataFrame()

#Creating instance of OpenAI
# client = OpenAI(
#     api_key="voc-46483699822398553210506a980a123bda52.03289710",
#     base_url="https://openai.vocareum.com/v1"
#)
client = AsyncOpenAI(
     api_key="voc-97047313922398553210506aae29fd599be5.07840606",
     base_url="https://openai.vocareum.com/v1"
 )





def prompt_zero_shot(snippets: str):
    """Strategy 1 — zero-shot. Just ask, no examples, no persona."""
    return f"""You are an AI assistant tasked to extract accurate and grounded information.
Extract the company, role and minimum years of experience from this job text in Jason format. If no years are stated, use null.
Text: "{snippets}"
Return as JSON with keys: "company", "role", "years_experience_required"."""


def prompt_few_shot(snippets: str):
    """Strategy 2 — few-shot. Provide clear examples to guide the model."""
    return f"""Extract the company, role, and minimum years of experience from the text where ever the information is not present use null.Extract company name role and minimum years of experience from this job text in Jason format.
Example 1: "XYZ Corp seeks a Senior Engineer with 5+ years" -> {{"company": "XYZ", "role": "Senior Engineer", "years_experience_required": 5}}
Example 2: "Looking for   3 years experience candidate at Soylent Industries" -> {{"company": "Soylent Industries", "role":"null", "years_experience_required": 3}}

Target Text: "{snippets}"
Return as JSON with keys: "company", "role", "years_experience_required"."""

def prompt_structured(snippets: str):
    """Strategy 4 — role-based. Provide a strict data persona wrapper."""
    return f""" You are a specialist in extracting information from job posting.Extract Company name,role and yearas of experience from each job posting in json format. 

Text:"{snippets}"
Return as JSON with keys: "company", "role", "years_experience_required"."""



def prompt_cot(snippets: str) -> str:
    """Strategy 3 — CoT. Make the model think before extracting."""
    return f"""Think step-by-step to extract the information from this job text and provide in Jason format.
1. Identify the company name. 2. Identify the role. 3. Look closely for numerical experience requirements.

Text: "{snippets}"
Return a JSON object including your breakdown in a "reasoning" key alongside "company", "role", and "years_experience_required"."""

STRATEGIES = {
    'zero_shot': prompt_zero_shot,
    'few_shot': prompt_few_shot,
    'structured': prompt_structured,
    'cot': prompt_cot,
}

async def parse_job(prompt: str, strategy_name: str, snippet_id: str):
    import time
    from openai import AsyncOpenAI
    
    total_cost = 0.0
    latency = 0.0
    raw_content = ""
    
    try:
        start_time = time.time()
        # 1. Fire the prompt to the gpt-4o-mini model (Fixed Indentation)
        _client = AsyncOpenAI(
            api_key=os.environ.get("voc-97047313922398553210506aae29fd599be5.07840606"),
            base_url=os.environ.get("https://openai.vocareum.com/v1")
        ) 
        response = await _client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0 
            )
            # Calculating Latency inside the active context block
        latency = time.time() - start_time

            # 2. Extract the text response returned 
        raw_content = response.choices[0].message.content

         # 3. Extract Token Usage & Calculate Cost
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        input_cost = prompt_tokens * (0.15 / 1_000_000)
        output_cost = completion_tokens *(0.60 / 1_000_000)
        total_cost = input_cost + output_cost

    except Exception as e:
        # 3. If the network drops or API fails, log the error instead of crashing
        if latency == 0.0:  # Calculate fallback latency if it failed inside client
            latency = time.time() - start_time
        raw_content = f"API Error: {str(e)}"
      
    # 4. Return everything packaged inside your tracking object
    return JobExtractionResult(
        job_id=snippet_id,
        strategy_name=strategy_name,
        prompt_sent=prompt,
        raw_response=raw_content,
        total_cost_usd=total_cost,
        latency_seconds=latency
    )



async def run_four_strategies(jobtxt: str, jid: str):
    """Run all four prompting strategies on a single job snippet."""
    
    tasks = [
        parse_job(
            prompt=strategy_func(jobtxt),  
            strategy_name=strategy_name,
            snippet_id=jid,
            #client=client
        )
        for strategy_name, strategy_func in STRATEGIES.items()
    ]     
    return await asyncio.gather(*tasks)
        

async def singlejob_run():
    # 1. Initialize variables (Indented 4 spaces)
    # job_id = "UNKNOWN_ID"
    # job_text = ""
    results_text = []

    # 2. Try block
    try:
        # Data loaded in  to Job_snippets 
        job_snippets = snippets[0]
        job_id = job_snippets["id"]
        job_text = job_snippets['snippet']
        
        
        print(f"🚀 Running 4 strategies concurrently for Job ID: {job_id}...")
        results_text = await run_four_strategies(job_text, job_id)
         
        print("\n🤖EXTRACTED RESULTS FOR EACH STRATEGY:\n")
        for result in results_text:

            print(f"--- Single Call Response ---") 
            print(f"🔹 [Strategy Name: {result.strategy_name.upper()}]")
            print(f"Job ID: {result.job_id}")
            print(f"Prompt Sent:\n{result.prompt_sent}\n")
            print(f"Raw Response:\n{result.raw_response}\n")
            print(f"Cost:{result.total_cost_usd:.6f}\n")
            print(f"Latency:{result.latency_seconds} seconds\n")
            print("-" * 40 + "\n")
            print(f"Succesfully Extracted")

       # 3. Build the DataFrame with ONLY strategy_name and raw_response columns
        results_df = pd.DataFrame([res.model_dump() for res in results_text])
        results_df.to_csv('results.csv', index=False)
        print(f"💾 Success! Saved {len(results_df)} rows to 'results.csv'.")

    #Exception block      
    except Exception as e:
        print(f"❌ An unexpected error occurred during execution: {e}")



async def run_all_jobs():
    # 1. Initialize variables (Indented 4 spaces)
    results_text = []
    tasks = []
    
    # 2. Try block
    try:
        job_snippets = snippets
        
        # NESTED LOOPS: Process every strategy for EVERY job
        for job in job_snippets:
            jid = job["id"]
            jobtxt = job["snippet"]
        
            for strategy_name, strategy_func in STRATEGIES.items():
                # Build the async task execution payload
                task = parse_job(
                    prompt=strategy_func(jobtxt),  
                    strategy_name=strategy_name,
                    snippet_id=jid,
                )
                tasks.append(task)
            
        print(f"🚀 Scheduled {len(tasks)} total LLM requests. Executing concurrently...")
        
        # MOVE GATHER OUTSIDE THE LOOPS: Fire all 40 tasks exactly ONCE
        results_text = await asyncio.gather(*tasks)
                
        print("\n🤖EXTRACTED RESULTS FOR EACH STRATEGY:\n")
        for result in results_text:
            print(f"--- All Job Response ---") 
            print(f"🔹 [Strategy Name: {result.strategy_name.upper()}]")
            print(f"Job ID: {result.job_id}")
            print(f"Prompt Sent:\n{result.prompt_sent}\n")
            print(f"Raw Response:\n{result.raw_response}\n")
            print(f"Cost: ${result.total_cost_usd:.6f}\n")
            print(f"Latency: {result.latency_seconds:.2f} seconds\n")
            print("-" * 40 + "\n")
            print(f"Successfully Extracted")

        # 3. Build the DataFrame OUTSIDE of the printing loop (Fixed Indentation)
        results_df = pd.DataFrame([res.model_dump() for res in results_text])
        
        # Clean formatting for the CSV fields to avoid scientific notation exponent text
        results_df['total_cost_usd'] = results_df['total_cost_usd'].map(lambda x: f"{x:.6f}")
        results_df['latency_seconds'] = results_df['latency_seconds'].map(lambda x: f"{x:.2f}")
        
        # Save to your desired file path
        results_df.to_csv('allresults.csv', index=False)
        print(f"💾 Success! Saved {len(results_df)} clean formatted rows to 'allresults.csv'.")
       
    # Exception block      
    except Exception as e:
        print(f"❌ An unexpected error occurred during execution: {e}")


async def main():
   
 await singlejob_run() 
 await run_all_jobs()    
      
   

#  main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
   
    
            
        
       
    

    



      




  
 
 

    
 
    


