
import asyncio
from asyncio import tasks
from http import client
import os
import re
import time
import sys
import csv
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
from openai import BaseModel, OpenAI

import openai
import pandas as pd
from Load_data import  getdata
import json
from setup import MODEL, JUDGE_MODEL, TEMPERATURE, RATES,client
from pydantic import BaseModel


# Define Structured for extraction result
class JobExtractionResult(BaseModel):
    job_id: str 
    strategy_name: str
    prompt_sent: str
    raw_response: str
    total_cost_usd:float
    latency_seconds:float

#Getting the data from Load_data.py
snippets, golden = getdata()
results_df = pd.DataFrame()

# Calculating score using LLM as judge
async def score_llm_judge(snippet_text: str, extracted: dict | None, gold: dict) -> int:

    client1=client
    if not extracted:
        return 1

    judge_prompt = f"""
    You are an expert objective AI evaluation judge. Score this extraction against Gold data using a 1-4 rubric.
    [Snippet] {snippet_text}
    [Gold] {json.dumps(gold)}
    [Extracted] {json.dumps(extracted)}
    Rubric: 4=all correct, 3=two correct, 2=one correct/fabricated, 1=none correct.
    Output ONLY a single integer (1, 2, 3, or 4). No explanations.
    """
    try:
        response = await client1.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.0
        )
        match = re.search(r'[1-4]', response.choices[0].message.content)
        return int(match.group()) if match else 1
    except Exception:
        return 1
    
# All Four Promp Stragies defined
def prompt_zero_shot(snippets: str):
    """Strategy 1 — zero-shot. Just ask, no examples, no persona."""
    return f"""You are an AI assistant tasked to extract accurate and grounded information.
Extract the company, role and minimum years of experience from this job text in Jason format. If no years are stated, use null.
Text: "{snippets}"
Return as JSON with keys: "company", "role", "years_experience_required"."""

def prompt_few_shot(snippets: str):
    """Strategy 2 — few-shot. Provide clear examples to guide the model."""
    return f"""Extract the company, role, and minimum years of experience from the text.Extract company name role and minimum years of experience from this job text in Jason format.
Example 1: "XYZ Corp seeks a Senior Engineer with 5+ years" -> {{"company": "XYZ", "role": "Senior Engineer", "years_experience_required": 5}}
Example 2: "Looking for   3 years experience candidate at Soylent Industries" -> {{"company": "Soylent Industries", "role":"null", "years_experience_required": 3}}

Target Text: "{snippets}"
Return as JSON with keys: "company", "role", "years_experience_required"."""

def prompt_structured(snippets: str):
    """Strategy 4 — role-based. Provide a strict data persona wrapper."""
    return f""" You are a specialist in extracting information from job posting.Extract Company name,role and yearas of experience from each job posting in json format.
  

Text:"{snippets}"
Return as JSON with keys: "company", "role", "years_experience_required"."""

def prompt_cot(snippet_text: str) -> str:
    """Strategy 4 — chain-of-thought. Ask the model to reason before answering."""
    return f"""Think step-by-step to extract the information from this job text. 
First, break down your analysis step-by-step, then provide the final output.

Field Fallback Rules:
- If a specific field cannot be found, set its value to null.
- For "years_experience_required", extract a string range (e.g., "3-5") if present. If no minimum experience or years are stated in the text, explicitly set it to null.

Text: "{snippet_text}"

Return as JSON with keys: "company", "role", "years_experience_required"."""

#Stratagies
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
    client_instance=client
    try:
        
        # 1. Firing  the prompt to the gpt-4o-mini model
        start_time = time.time()
        response = await client_instance.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0 
            )
            # Calculating Latency
        latency = time.time() - start_time

            # Extracting the text response returned 
        raw_content = response.choices[0].message.content

         # Token Usage & Cost Calculation
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        input_cost = prompt_tokens * (0.15 / 1_000_000)
        output_cost = completion_tokens *(0.60 / 1_000_000)
        total_cost = input_cost + output_cost

    except Exception as e:
       
        if latency == 0.0:  
            latency = time.time() - start_time
        raw_content = f"API Error: {str(e)}"
      
   
    return JobExtractionResult(
        job_id=snippet_id,
        strategy_name=strategy_name,
        prompt_sent=prompt,
        raw_response=raw_content,
        total_cost_usd=total_cost,
        latency_seconds=latency
    )

async def run_four_strategies(jobtxt: str, jid: str):
    "Run all four prompting strategies on a single job snippet."""
    
    tasks = [
        parse_job(
            prompt=strategy_func(jobtxt),  
            strategy_name=strategy_name,
            snippet_id=jid,
            #client_instance=client
        )
        for strategy_name, strategy_func in STRATEGIES.items()
    ]     
    return await asyncio.gather(*tasks)
           
# Running single job
async def singlejob_run():
   
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

       # 3. Building the DataFrame 
        results_df = pd.DataFrame([res.model_dump() for res in results_text])
        results_df.to_csv('results.csv', index=False)
        print(f"💾 Success! Saved {len(results_df)} rows to 'results.csv'.")

    #Exception block      
    except Exception as e:
        print(f"❌ An unexpected error occurred during execution: {e}")

# Running all 40 Jobs
async def run_all_jobs():

    golden_rule=golden
    results_text = []
    tasks = []
    
    #  Try block
    try:
        job_snippets = snippets
        
        # Process every strategy for every job
        for job in job_snippets:
            jid = job["id"]
            jobtxt = job["snippet"]
        
            for strategy_name, strategy_func in STRATEGIES.items():
                # async task execution payload
                task = parse_job(
                    prompt=strategy_func(jobtxt),  
                    strategy_name=strategy_name,
                    snippet_id=jid,
                    #client_instance=client
                )
                tasks.append(task)
            
        print(f"Scheduled {len(tasks)} total LLM requests. Executing concurrently...")
        
        # Fire all 40 tasks exactly ONCE
        results_text = await asyncio.gather(*tasks)
                
        print("\n EXTRACTED RESULTS FOR EACH STRATEGY:\n")
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

        # 3. Building  the DataFrame 
        results_df = pd.DataFrame([res.model_dump() for res in results_text])
        results_df['total_cost_usd'] = results_df['total_cost_usd'].map(lambda x: f"{x:.3f}")
        results_df['latency_seconds'] = results_df['latency_seconds'].map(lambda x: f"{x:.2f}")
        
        # Saving the  file 
        results_df.to_csv('allresults.csv', index=False)
        print(f"💾 Success! Saved {len(results_df)} clean formatted rows to 'allresults.csv'.")
        
    
    # 3. Loop through each result row inside results_text
        all_scores = []
        judge_tasks = []  
        valid_meta = []
        
        for res in results_text:
            if isinstance(res, Exception) or "API Error" in str(res.raw_response):
                all_scores.append(0) 
                continue
                
            # Safe lookup: stops the script from crashing if an ID is missing
            gold_truth = golden_rule.get(res.job_id)
            if not gold_truth:
                print(f"⚠️ Warning: Job ID {res.job_id} not found in golden_rule.")
                all_scores.append(0)
                continue
    
            # Convert the raw LLM string response into a real Python dictionary
            parse_success = False
            try:
                cleaned_json = res.raw_response.strip().replace("```json", "").replace("```", "").strip()
                extracted_dict = json.loads(cleaned_json)
                parse_success = True 
            except Exception:
                extracted_dict = {}  
                parse_success = False

            #Calculating Accuracy score
            score_res = score_accuracy(extracted_dict, gold_truth)
            
            all_scores.append(score_res)
            print(f"📊 Job ID {res.job_id} [{res.strategy_name}]: Score = {score_res}/3 | Parse Success = {parse_success}")

            # Find the original snippet text from your job_snippets list to pass to the judge
            original_job = next((j for j in job_snippets if j["id"] == res.job_id), None)
            snippet_text = original_job["snippet"] if original_job else ""

            #TRIGGER THE ASYNC LLM JUDGE TASK
            task_judge = asyncio.create_task(
                score_llm_judge(snippet_text, extracted_dict, gold_truth)
            )
            judge_tasks.append(task_judge)
             # Keep aligned row metadata so we zip columns perfectly later
            valid_meta.append({
                "job_id": res.job_id,
                "strategy_name": res.strategy_name,
                "calculated_score": score_res,
                "parse_success": parse_success
            })
             # FIRE ALL GPT-4o JUDGE CONNECTIONS AT ONCE 
        print(f"\n🚀 Firing {len(judge_tasks)} evaluation streams concurrently to GPT-4o Judge...")
        judge_scores = await asyncio.gather(*judge_tasks, return_exceptions=True)

        # Open and write both scores side-by-side to your file
        score_csv_filename = "job_evaluation_scores.csv"
        score_headers = ["job_id", "strategy_name", "calculated_score","parse_success", "llm_judge_score"]
        
        with open(score_csv_filename, mode="w", newline="", encoding="utf-8") as score_file:
            score_writer = csv.DictWriter(score_file, fieldnames=score_headers)
            score_writer.writeheader()
            
            # Zip aligned tracking details with completed LLM Judge ratings arrays
            for meta, j_score in zip(valid_meta, judge_scores):
                actual_judge_rating = j_score if isinstance(j_score, int) else 1
                
                score_writer.writerow({
                    "job_id": meta["job_id"],
                    "strategy_name": meta["strategy_name"],
                    "calculated_score": f"{meta['calculated_score']}/3",
                    "parse_success": meta["parse_success"],
                    "llm_judge_score": f"{actual_judge_rating}/4"  # 💡 Injected judge column here
                })
            
           
            print(f"🎉 Successfully saved score metrics separately to '{score_csv_filename}'!")
        
        # =====================================================================
        # 📊 GENERATE, FORMAT AND EXPORT STRUCTURAL SUMMARY TABLE
        # =====================================================================
        combined_records = []
        
        # Loop strictly by range length to keep alignments identical across pools
        for i in range(len(results_text)):
            res = results_text[i]
            
            # Fetch elements dynamically with fallback options to protect against structural errors
            meta = valid_meta[i] if i < len(valid_meta) else {}
            j_score = judge_scores[i] if i < len(judge_scores) else 1.0
            
            cost = float(res.total_cost_usd) if hasattr(res, 'total_cost_usd') else 0.0
            latency = float(res.latency_seconds) if hasattr(res, 'latency_seconds') else 0.0
            actual_judge_rating = j_score if isinstance(j_score, (int, float)) else 1.0
            
            # Safe recovery fallback for strategy key parameters
            strat_name = meta.get("strategy_name") if isinstance(meta, dict) else getattr(res, 'strategy_name', 'unknown')
            calc_score = meta.get("calculated_score", 0) if isinstance(meta, dict) else 0
            p_success = meta.get("parse_success", False) if isinstance(meta, dict) else False

            combined_records.append({
                "Strategy": strat_name,
                "Accuracy_Raw": calc_score,
                "Parse_Rate_Raw": 1 if p_success else 0,
                "Judge_Score_Raw": actual_judge_rating,
                "Cost_Raw": cost,
                "Latency_Raw": latency
            })
            
        summary_df = pd.DataFrame(combined_records)
        
        # Safety gate prevents KeyErrors if DataFrame is blank
        if summary_df.empty or "Strategy" not in summary_df.columns:
            print("⚠️ Cannot compile table: Strategy data tracking columns are unpopulated or misaligned.")
            return

        # Safe to aggregate now because the column mapping targets are verified
        grouped = summary_df.groupby("Strategy").agg(
            accuracy_mean=("Accuracy_Raw", "mean"),
            parse_rate=("Parse_Rate_Raw", "mean"),
            judge_mean=("Judge_Score_Raw", "mean"),
            cost_sum=("Cost_Raw", "sum"),
            latency_p50=("Latency_Raw", "median")
        ).reset_index()
        
        comparison_table = pd.DataFrame()
        comparison_table["Strategy"] = grouped["Strategy"]
        comparison_table["Accuracy (mean)"] = grouped["accuracy_mean"].map(lambda x: f"{x:.1f} / 3")
        comparison_table["Parse rate"] = grouped["parse_rate"].map(lambda x: f"{x * 100:.0f}%")
        comparison_table["Judge score"] = (grouped["judge_mean"] * 6.25).map(lambda x: f"{x:.1f} / 25")
        comparison_table["Cost ($)"] = grouped["cost_sum"].map(lambda x: f"${x:.5f}")
        comparison_table["Latency p50 (s)"] = grouped["latency_p50"].map(lambda x: f"{x:.1f}s")
        
        # Saving native Markdown table document layout
        try:
            markdown_table_string = comparison_table.to_markdown(index=False)
            with open("mp1_comparison.md", "w", encoding="utf-8") as md_file:
                md_file.write("# Strategy  Comparison Table\n\n")
                md_file.write(markdown_table_string)
                md_file.write("\n")
            print("💾 Saved natively formatted Markdown table directly to 'mp1_comparison.md'.")
        except Exception as md_err:
            print(f"⚠️ Could not write Markdown file natively (missing tabulate module?): {md_err}")

        # Print out clean preview layout inside your current execution window
        print("\n📈 STRATEGY COMPARISON SUMMARY:")
        try:
            from tabulate import tabulate
            print(tabulate(comparison_table, headers='keys', tablefmt='grid', showindex=False))
        except ImportError:
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(comparison_table.to_string(index=False))  

    except Exception as e:
        print(f"❌ An unexpected error occurred during execution: {e}")


# Calculating Accuracy score
def score_accuracy(extracted: dict | None, gold: dict) -> int:
    """Compare 3 fields. Case-insensitive, whitespace-trimmed for strings. Return 0 to 3."""
    if not extracted:
        return 0
        
    score = 0
    target_fields = ["company", "role", "years_experience_required"]
    
    for field in target_fields:
        ext_val = str(extracted.get(field, "")).strip().lower()
        gold_val = str(gold.get(field, "")).strip().lower()
        
        if ext_val == gold_val and gold_val != "":
            score += 1
    print(score)       
    return score


async def main():
 await singlejob_run() 
 await run_all_jobs()          


#  main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
   
    
            
        
       
    

    



      




  
 
 

    
 
    


