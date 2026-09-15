"""pipeline.py — Week 2 hands-on starter.

We'll fill in the TODOs together during the live session. The pieces:

    Step 2 — async def ask_llm                 (one call)
    Step 3 — ask_llm_with_retry                (exponential backoff)
    Step 4 — run_batch with asyncio.gather     (parallel fan-out)
    Step 5 — JSON-formatted structured logging

For the live demo we call ``fake_ask_llm`` from ``fake_llm.py`` —
no API quota, no network flakiness, and a ``fail_rate`` knob so retries
fire on demand. In the lab you'll swap to the real ``AsyncOpenAI`` client
(same ``Question``/``Answer`` shape — only one import changes).

Run it (after the TODOs are filled):
    python pipeline.py           # fail_rate = 0.0  (clean parallel run)
    python pipeline.py 0.4       # fail_rate = 0.4  (forces retries)
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json
from json import tool
import logging
#import os
import time

from fastapi import logger
from openai import AsyncOpenAI, AsyncOpenAI, OpenAI
from pydantic import schema
from .settings import Settings
from src.pipeline.cost import compute_cost_usd

# Live-session stand-in. Same Pydantic shape as the real call.
from .fake_llm import Question, Answer, fake_ask_llm, FakeLLMError
#from .pipeline import pipeline
#from .logging_config import get_logger
#log = get_logger()


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

ANSWER_TOOL = {
    'type': 'function',
    'function': {
        'name': 'answer_tool',
        'description': 'Provide a detailed answer with confidence score and source tracking.',
        'parameters': {
            'type': 'object',
            'properties': {
                'content': {
                    'type': 'string',
                    'description': 'The answer to the query, restricted to 2 to 4 sentences.'
                },
                'confidence': {
                    'type': 'number',
                    'description': 'A confidence score between 0.0 and 1.0.'
                },
                'sources': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'An array of URLs or source IDs used to compile the answer.'
                }
            },
            'required': ['content', 'confidence', 'sources']
        }
    }
}




    



# ---------- Step 2: one async call ----------
async def ask_llm(q: Question, fail_rate: float = 0.0) -> Answer:
    """One call. Live demo: fake. Lab: real AsyncOpenAI (same signature)."""
    ans=await fake_ask_llm(q, fail_rate=fail_rate)
    log.info(json.dumps({"events":"asked", "question":q.text[:40]}))
    return ans
   
# ─── Real LLM call via tool-calling ─────────────────────────────────────────
async def ask_llm(q: Question, settings: Settings | None = None) -> Answer:
    """Call the LLM with tool-calling, returning a structured Answer.

    Retries on transient failures. Real cost computed from response.usage.
    """
    settings = settings or Settings()

    if settings.use_fake:
        content = await fake_ask_llm(q)
        return Answer(
    question=q.text,     # Pass the original question string
    text=content,        # Map the mock LLM result to 'text' instead of 'content'
    cost_usd=0.0,
    retries=0
)
        #return Answer(content=content, cost_usd=0.0, retries=0)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    last_err: Exception | None = None

# Change line 96 to fall back directly to the environment variable:
    #client = AsyncOpenAI(api_key=getattr(settings, "openai_api_key", os.getenv("OPENAI_API_KEY", "")))

 
    

    for attempt in range(settings.max_retries + 1):
        try:
            resp = await client.chat.completions.create(
                model=settings.model,
                messages=[{"role": "user", "content": q.question}],
                tools=[ANSWER_TOOL],
                tool_choice={
                    "type": "function",
                    "function": {"name": "answer_question"},
                },
            )

            # Parse the tool call's structured arguments.
            tool_calls = resp.choices[0].message.tool_calls or []
            if not tool_calls:
                # Defensive — should not happen because tool_choice forces it,
                # but if a provider misbehaves we want a clear error.
                raise RuntimeError("LLM did not call the answer_question tool")
            args_json = tool_calls[0].function.arguments
            args = json.loads(args_json)

            # Compute real cost from usage.
            usage = resp.usage
            cost = compute_cost_usd(
                settings.model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            )

            return Answer(
                content=args["content"],
                confidence=args["confidence"],
                sources=args.get("sources", []),
                cost_usd=cost,
                retries=attempt,
                schema_version="v1",
            )

        except Exception as exc:
            last_err = exc
            if attempt < settings.max_retries:
                logger.warning(
                    "ask_llm attempt %d failed: %s — retrying", attempt + 1, exc
                )
                await asyncio.sleep(settings.retry_delay_s * (2 ** attempt))
                continue
            raise

    raise RuntimeError(f"ask_llm exhausted retries: {last_err}")  # unreachable

# ─── Streaming endpoint (Step 2a, 2b) ───────────────────────────────────────
async def stream_answer(question: str, settings: Settings | None = None) -> AsyncIterator[str]:
    """Yield content tokens as they arrive from the LLM.

    W3 simulated this with asyncio.sleep. W4 replaces with real chunks.
    """
    settings = settings or Settings()

    if settings.use_fake:
        # Offline path — yield words slowly. Kept for tests.
        full = await fake_ask_llm(question)
        for word in full.split(" "):
            await asyncio.sleep(0.05)
            yield word + " "
        return

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # TODO Step 2a — call client.chat.completions.create with stream=True:
    #   stream = await client.chat.completions.create(
    #       model=settings.model,
    #       messages=[{"role": "user", "content": question}],
    #       stream=True,
    #   )
    #
    # TODO Step 2b — iterate and yield:
    #   async for chunk in stream:
    #       delta = chunk.choices[0].delta
    #       if delta.content:
    #           yield delta.content

    raise NotImplementedError("Steps 2a, 2b — fill these in")
    
# ---------- Step 3: retry with exponential backoff ----------
async def ask_llm_with_retry(
    q: Question, tries: int = 3, fail_rate: float = 0.0
) -> Answer:
    """Retry up to ``tries`` times. Wait 1 s, 2 s, 4 s between attempts."""
    # TODO (Step 3):
    for attempt in range(tries):
        try:
            ans = await ask_llm(q, fail_rate=fail_rate)
            ans.retries = attempt
            return ans
        except FakeLLMError as exc:
            if attempt == tries - 1:
                raise
            log.warning(json.dumps({"event": "retry", "attempt": attempt + 1, "question": q.text[:40], "error": str(exc)}))
            await asyncio.sleep(2 ** attempt)

   
   


# ---------- Step 4: gather it all together ----------
# async def run_batch(
#     questions: list[Question], fail_rate: float = 0.0
# ) -> list[Answer]:
#     """Fire all questions in parallel via ``asyncio.gather``."""
#     # TODO (Step 4):
#     tasks = [ask_llm_with_retry(q, fail_rate=fail_rate) for q in questions]
#     return await asyncio.gather(*tasks)

async def run_batch_stream(questions: list[Question], fail_rate: float = 0.0) -> list[Answer]:
    tasks = [ask_llm_with_retry(q, fail_rate=fail_rate) for q in questions]
    results: list[Answer] = []
    for coro in asyncio.as_completed(tasks):
        ans = await coro
        print(f"  ✓ {ans.text[:60]}...")            # arrives the instant it's ready
        results.append(ans)
    return results
    
   

# ---------- Step 5: structured (JSON) logging ----------
# TODO (Step 5):
class JsonFormatter(logging.Formatter): 
        def format(self, record: logging.LogRecord) -> str:
            return json.dumps({
            "ts":     round(time.time(), 3),
            "level":  record.levelname,
            "msg":    record.getMessage(),
            "logger": record.name,
        })
log = logging.getLogger("pipeline"); 
log.setLevel(logging.INFO)
handler = logging.StreamHandler();
handler.setFormatter(JsonFormatter()) 
log.addHandler(handler)

        

# ---------- main ----------
    # if __name__ == "__main__":
    
    #  import sys

    # fail_rate = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    # sample = [
    #     Question(text="What is RAG in one sentence?"),
    #     Question(text="Name three uses of vector databases."),
    #     Question(text="Why might an LLM hallucinate?"),
    # ]
    # started = time.time()
    # answers = asyncio.run(run_batch(sample, fail_rate=fail_rate))
    # elapsed = time.time() - started
    # print(f"\n{len(answers)} answers in {elapsed:.2f}s\n")
    # for a in answers:
    #     print(f"- {a.text[:80]}") #

if __name__ == "__main__":
    import sys
    fail_rate = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    sample = [Question(text=t) for t in [
        "What is RAG in one sentence?",
        "Name three uses of vector databases.",
        "Why might an LLM hallucinate?",
        "Explain async and await in plain language.",
        "What is the difference between a chatbot and an agent?",
    ]]
    print(f"\nrun_batch_stream — fail_rate={fail_rate}")
    answers = asyncio.run(run_batch_stream(sample, fail_rate=fail_rate))
    print(f"\nreturned {len(answers)} answers")