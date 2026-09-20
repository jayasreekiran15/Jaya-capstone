### 3a — Malformed JSON

1 jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ curl -i -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{}'
HTTP/1.1 422 Unprocessable Content
date: Fri, 11 Sep 2026 06:36:04 GMT
server: uvicorn
content-length: 91
content-type: application/json

{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required","input":{}}]}

2 jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ curl -i -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"q": "What is the leave policy?"}'
HTTP/1.1 422 Unprocessable Content
date: Fri, 11 Sep 2026 06:37:02 GMT
server: uvicorn
content-length: 122
content-type: application/json

{"detail":[{"type":"missing","loc":["body","question"],"msg":"Field required","input":{"q":"What is the leave policy?"}}]}


3 jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ curl -i -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": 42}'
HTTP/1.1 422 Unprocessable Content
date: Fri, 11 Sep 2026 06:39:48 GMT
server: uvicorn
content-length: 111
content-type: application/json

{"detail":[{"type":"string_type","loc":["body","question"],"msg":"Input should be a valid string","input":42}]}

4 jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ curl -i -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the leave policy?"'
HTTP/1.1 422 Unprocessable Content
date: Fri, 11 Sep 2026 06:40:37 GMT
server: uvicorn
content-length: 133
content-type: application/json

{"detail":[{"type":"json_invalid","loc":["body",40],"msg":"JSON decode error","input":{},"ctx":{"error":"Expecting ',' delimiter"}}]}

### 3b — 5000-character question 

jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ LONG_Q=$(python -c "print('Please summarize the company policy on remote work. ' * 100)")
echo "Length: ${#LONG_Q}"
Length: 5200

jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ time curl -N -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d "$(printf '{"question": "%s"}' "$LONG_Q")"
(simulated answer) A grounded, concise response to: Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policyon remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remotework. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work.Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work. Please summarize the company policy on remote work.  
real    0m49.278s
user    0m0.060s
sys     0m0.062s


### 3c — Disconnect mid-stream

On the client side:

```
Please give me                          ← some words
curl: (28) Operation timed out          ← curl bails
```

On the server side (in the uvicorn log), look for:

jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ curl http://localhost:8000/health
{"status":"ok"}

###3d — 50 parallel requests


jayas@reyanshkiruthik MINGW64 ~/Jaya-capstone (main)
$ python scripts/stress_test.py --requests 50 --concurrent 10
Stress test: 50 requests, up to 10 concurrent
────────────────────────────────────────────────────────────
Total wall time:   9.50s
Successes:         50 / 50
Effective req/s:   5.27

Latency (successful requests):
  min:   1.02s
  p50:   1.77s
  p95:   2.40s
  max:   2.65s

