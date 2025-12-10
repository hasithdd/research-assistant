"""Unified LLM client with OpenAI -> vLLM fallback."""

from typing import List, Dict, Optional
import time
from app.core.config import settings
from app.utils.logger import log_llm_call, logger


def _strip_reasoning_tags(text: str) -> str:
    """Remove reasoning blocks like <think>...</think> from model output.

    Some providers (including vLLM-served models) may return hidden reasoning
    sections wrapped in <think>...</think>. We strip those before sending the
    answer back to the client so the user only sees the final response.
    """
    if not text:
        return text

    start = text.find("<think>")
    if start == -1:
        return text

    end = text.find("</think>", start)
    if end != -1:
        # Drop the entire <think>...</think> block and keep what follows.
        cleaned = text[end + len("</think>") :]
        return cleaned.strip() or cleaned

    # If there's no closing tag, drop everything from the opening tag onwards.
    cleaned = text[:start]
    # Prefer returning an empty string over leaking chain-of-thought.
    return cleaned.strip()


def _truncate_prompt(prompt: str, max_tokens: int = 400) -> str:
    """Truncate prompt to fit within token budget (rough estimate: 1 token ≈ 4 chars)."""
    max_chars = max_tokens * 4
    if len(prompt) <= max_chars:
        return prompt
    
    # Keep beginning and end, truncate middle
    keep_each = max_chars // 2
    return f"{prompt[:keep_each]}\n\n[... content truncated ...]\n\n{prompt[-keep_each:]}"


def _call_vllm(messages: List[Dict[str, str]], max_tokens: int = 250, temperature: float = 0.0) -> Optional[str]:
    """Call vLLM-compatible endpoint (OpenAI API format)."""
    if not settings.USE_VLLM_FALLBACK:
        return None
    
    start_time = time.time()
    try:
        import openai
        
        # Create a separate client for vLLM
        vllm_client = openai.OpenAI(
            api_key="EMPTY",  # vLLM doesn't require key
            base_url=settings.VLLM_BASE_URL,
        )
        
        # Truncate messages to fit 1024 token limit (leave room for completion)
        truncated_messages = []
        for msg in messages:
            truncated_msg = msg.copy()
            if msg["role"] == "user":
                truncated_msg["content"] = _truncate_prompt(msg["content"], max_tokens=700)
            truncated_messages.append(truncated_msg)
        
        # Adjust max_tokens to fit within model's 1024 token budget
        safe_max_tokens = min(max_tokens, 200)
        
        # Estimate prompt tokens (rough: 1 token ≈ 4 chars)
        prompt_text = " ".join([m["content"] for m in truncated_messages])
        estimated_prompt_tokens = len(prompt_text) // 4
        
        resp = vllm_client.chat.completions.create(
            model="unsloth/Qwen3-1.7B-unsloth-bnb-4bit",
            messages=truncated_messages,
            max_tokens=safe_max_tokens,
            temperature=temperature,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        raw_result = resp.choices[0].message.content.strip()
        result = _strip_reasoning_tags(raw_result)
        completion_tokens = len(result) // 4
        
        log_llm_call(
            provider="vLLM",
            model="Qwen3-1.7B-4bit",
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=completion_tokens,
            success=True,
            latency_ms=latency_ms
        )
        
        return result
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"vLLM fallback failed: {e}")
        log_llm_call(
            provider="vLLM",
            model="Qwen3-1.7B-4bit",
            prompt_tokens=0,
            completion_tokens=0,
            success=False,
            error=str(e),
            latency_ms=latency_ms
        )
        return None


def call_llm(
    messages: List[Dict[str, str]], 
    max_tokens: int = 250, 
    temperature: float = 0.0,
    model: str = "gpt-4o-mini"
) -> str:
    """
    Call LLM with fallback logic:
    1. Try OpenAI if API key present
    2. Fall back to vLLM if configured
    3. Return first user message content truncated as last resort
    """
    
    # Try OpenAI first - skip if key is empty or starts with #
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and not settings.OPENAI_API_KEY.startswith("#"):
        start_time = time.time()
        try:
            import openai
            
            # Use v1.0+ client syntax
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            raw_result = resp.choices[0].message.content.strip()
            result = _strip_reasoning_tags(raw_result)
            
            log_llm_call(
                provider="OpenAI",
                model=model,
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                success=True,
                latency_ms=latency_ms
            )
            
            return result
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning(f"OpenAI call failed: {e}, trying vLLM fallback...")
            log_llm_call(
                provider="OpenAI",
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                success=False,
                error=str(e),
                latency_ms=latency_ms
            )
    
    # Try vLLM fallback
    vllm_result = _call_vllm(messages, max_tokens, temperature)
    if vllm_result:
        return vllm_result
    
    # Last resort: NEVER echo the prompt back to the user.
    # Return a safe, generic message instead.
    logger.error("All LLM providers failed, returning safe fallback text instead of prompt")
    return "No response available from the language model."
