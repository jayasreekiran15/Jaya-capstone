# tests/test_pipeline.py
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, patch
from src.pipeline.fake_llm import Answer
from src.pipeline.pipeline import Question

# Assuming FakeLLMError is defined in your pipeline module or errors module
from src.pipeline.pipeline import FakeLLMError 

@pytest.mark.asyncio
async def test_ask_llm_calls_fake_once():
    # Arrange
    fake_answer = Answer(
        question="What is the capital of France?",
        text="Mocked answer.",
        cost_usd=0.002,
        retries=0
    )
    
    # Act
    with patch("src.pipeline.pipeline.fake_ask_llm", AsyncMock(return_value=fake_answer)) as mock_fake:
        # Import inside the patched block so it grabs the mocked dependency
        from src.pipeline.pipeline import ask_llm
        
        question = Question(text="What is the capital of France?")
        result = await ask_llm(question)
        
    # Assert
    assert mock_fake.call_count == 1
    assert result.text == "Mocked answer."



@pytest.mark.asyncio
async def test_retry_three_times_on_failure():
    # Arrange
    # Patch the LLM function to always fail
    with patch("src.pipeline.pipeline.fake_ask_llm", new_callable=AsyncMock) as mock_fake_ask_llm, \
         patch("src.pipeline.pipeline.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
         
        mock_fake_ask_llm.side_effect = FakeLLMError("simulated")
        
        # Act
        from src.pipeline.pipeline import ask_llm_with_retry

         # Wrap the string so q.text evaluates correctly
        dummy_question = SimpleNamespace(text="test question")
        
        # Verify the exception eventually propagates out after exhaustion
        with pytest.raises(FakeLLMError):
            await ask_llm_with_retry(q=dummy_question, tries=3)
            
        # Assert
        # Verify that it attempted exactly 3 times before giving up
        assert mock_fake_ask_llm.call_count == 3

