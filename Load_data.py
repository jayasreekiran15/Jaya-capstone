import json
from pathlib import Path


def getdata():
    DATA_DIR = Path('data')   # adjust if your folder layout differs

    snippets = [json.loads(line) for line in (DATA_DIR / 'job_snippets.jsonl').read_text().splitlines() if line.strip()]
    golden = {row['id']: row for row in (json.loads(line) for line in (DATA_DIR / 'golden_set.jsonl').read_text().splitlines() if line.strip())}

    #print(f'Loaded {len(snippets)} snippets, {len(golden)} golden entries.')
    #print('Sample snippet:', snippets[0])
    
    return snippets, golden
 