"""
ADK model adapter for Groq — the college MVP's only LLM provider.

ADK's first-class model is Gemini; other providers normally go through
LiteLLM. We deliberately do NOT take the LiteLLM dependency: its
install pulls boto3/tokenizers/huggingface-hub (~150MB) into the
Vercel function bundle and seconds into every cold start. Groq serves
an OpenAI-compatible chat-completions API, so the whole adapter is
this one class: translate ADK's LlmRequest (genai contents + function
declarations) to a Groq chat call, translate the response back into an
LlmResponse (text + function calls). All HTTP goes through
backend.core.llm.groq_chat, so timeouts and the error taxonomy are the
same as the direct legs.

The translators are pure functions and unit-tested offline
(backend/tests/test_college_groq_provider.py) — the mentor's tool
loops depend on function-call / function-response fidelity.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types

from backend.core.llm import groq_chat


def _normalize_schema(node: Any) -> Any:
    """
    Convert a FunctionDeclaration schema dict into the JSON-schema
    subset Groq/OpenAI function calling accepts. Two source flavors
    reach here:

    - genai's classic ``parameters``: proto enum type strings
      ("OBJECT", "STRING") that must be lowercased.
    - ADK 2.x's ``parameters_json_schema``: a pydantic-flavored JSON
      schema where Optional[X] is ``anyOf: [X, {"type": "null"}]``
      (OpenAI-style endpoints reject the null branch) and every node
      carries a cosmetic ``title``.

    So: lowercase type strings, collapse an anyOf/oneOf whose branches
    are exactly [X, null] down to X, and strip ``title`` keys.
    Everything else (properties, required, enum, description) passes
    through recursively.
    """
    if isinstance(node, dict):
        for combiner in ("anyOf", "oneOf"):
            branches = node.get(combiner)
            if isinstance(branches, list) and len(branches) == 2:
                nulls = [b for b in branches
                         if isinstance(b, dict)
                         and str(b.get("type", "")).lower() == "null"]
                others = [b for b in branches if b not in nulls]
                if len(nulls) == 1 and len(others) == 1:
                    merged = dict(others[0]) if isinstance(
                        others[0], dict) else {}
                    for key, value in node.items():
                        if key in (combiner, "title", "default"):
                            continue
                        merged.setdefault(key, value)
                    return _normalize_schema(merged)
        out: Dict[str, Any] = {}
        for key, value in node.items():
            if key in ("title", "default"):
                # Annotations, not constraints — some strict
                # function-calling validators reject them.
                continue
            if key == "properties" and isinstance(value, dict):
                # Keys here are property NAMES, not schema keys — a
                # parameter can literally be named "title" (the
                # commitment tool's) and must survive.
                out[key] = {name: _normalize_schema(schema)
                            for name, schema in value.items()}
            elif key == "type" and isinstance(value, str):
                out[key] = value.lower()
            else:
                out[key] = _normalize_schema(value)
        return out
    if isinstance(node, list):
        return [_normalize_schema(v) for v in node]
    return node


def _content_text(content) -> str:
    parts = []
    if isinstance(content, str):
        return content
    for part in (getattr(content, "parts", None) or []):
        text = getattr(part, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "".join(parts)


def translate_request(llm_request: LlmRequest):
    """
    LlmRequest → (messages, tools, max_tokens) for a Groq chat call.

    - config.system_instruction → leading system message
    - model contents → assistant messages (text + tool_calls)
    - function_response parts → OpenAI tool messages (tool_call_id
      preserved from the genai part id, falling back to the tool name)
    - config.tools' function declarations → OpenAI tool definitions
    - config.max_output_tokens → max_tokens
    """
    config = llm_request.config
    messages: List[Dict[str, Any]] = []

    system_instruction = getattr(config, "system_instruction", None)
    if system_instruction:
        system_text = system_instruction if isinstance(
            system_instruction, str) else _content_text(system_instruction)
        if system_text.strip():
            messages.append({"role": "system", "content": system_text})

    for content in (llm_request.contents or []):
        parts = getattr(content, "parts", None) or []
        role = getattr(content, "role", None) or "user"

        tool_results = [p for p in parts
                        if getattr(p, "function_response", None) is not None]
        for part in tool_results:
            fr = part.function_response
            response = getattr(fr, "response", None) or {}
            try:
                text = json.dumps(response)
            except Exception:
                text = str(response)
            messages.append({
                "role": "tool",
                "tool_call_id": getattr(fr, "id", None)
                or getattr(fr, "name", "") or "tool",
                "content": text,
            })

        calls = [p for p in parts
                 if getattr(p, "function_call", None) is not None]
        text = "".join(p.text for p in parts
                       if isinstance(getattr(p, "text", None), str))
        if calls:
            tool_calls = []
            for idx, part in enumerate(calls):
                fc = part.function_call
                args = getattr(fc, "args", None) or {}
                try:
                    arguments = json.dumps(args)
                except Exception:
                    arguments = "{}"
                tool_calls.append({
                    "id": getattr(fc, "id", None)
                    or f"call_{getattr(fc, 'name', 'tool')}_{idx}",
                    "type": "function",
                    "function": {"name": getattr(fc, "name", ""),
                                 "arguments": arguments},
                })
            messages.append({"role": "assistant",
                             "content": text or None,
                             "tool_calls": tool_calls})
        elif text:
            messages.append({
                "role": "assistant" if role == "model" else "user",
                "content": text,
            })

    tools: List[Dict[str, Any]] = []
    for tool in (getattr(config, "tools", None) or []):
        for fd in (getattr(tool, "function_declarations", None) or []):
            try:
                raw = fd.to_json_dict()
            except Exception:
                continue
            function: Dict[str, Any] = {"name": raw.get("name", "")}
            if raw.get("description"):
                function["description"] = raw["description"]
            # ADK 2.x emits the parameter schema as
            # ``parameters_json_schema`` (pydantic flavor); the classic
            # genai field is ``parameters``. Reading only the classic
            # field silently shipped every tool to the provider with
            # NO argument schema — the model could see the tools but
            # could never call them with arguments (transfer_to_agent
            # included), which is exactly how the mentor lost its tool
            # layer live. Genuinely arg-less tools get an explicit
            # empty object schema, which strict providers require.
            schema = raw.get("parameters") or raw.get(
                "parameters_json_schema")
            if schema:
                function["parameters"] = _normalize_schema(schema)
            else:
                function["parameters"] = {
                    "type": "object", "properties": {}}
            tools.append({"type": "function", "function": function})

    max_tokens = getattr(config, "max_output_tokens", None)
    return messages, tools, max_tokens


def translate_response(payload: Dict[str, Any]) -> LlmResponse:
    """Groq chat-completions JSON → ADK LlmResponse (text + calls)."""
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    parts: List[genai_types.Part] = []
    content_text = message.get("content")
    if isinstance(content_text, str) and content_text:
        parts.append(genai_types.Part(text=content_text))
    for tc in (message.get("tool_calls") or []):
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            args = {}
        if not isinstance(args, dict):
            args = {"value": args}
        parts.append(genai_types.Part(function_call=genai_types.FunctionCall(
            name=fn.get("name", ""), args=args, id=tc.get("id"))))
    usage_metadata = None
    usage = payload.get("usage") or {}
    if usage:
        usage_metadata = genai_types.GenerateContentResponseUsageMetadata(
            prompt_token_count=usage.get("prompt_tokens", 0),
            candidates_token_count=usage.get("completion_tokens", 0),
            total_token_count=usage.get("total_tokens", 0),
        )
    # Groq reports OpenAI finish reasons; genai's enum has no
    # "tool_calls" value (Gemini returns STOP with the calls in the
    # parts), so map onto the enum instead of passing raw strings.
    finish_reason = {"stop": "STOP", "length": "MAX_TOKENS",
                     "tool_calls": "STOP",
                     "content_filter": "PROHIBITED_CONTENT"}.get(
                         choice.get("finish_reason"))
    return LlmResponse(
        content=genai_types.Content(role="model", parts=parts),
        usage_metadata=usage_metadata,
        finish_reason=finish_reason,
        turn_complete=True,
    )


class GroqLlm(BaseLlm):
    """
    ADK BaseLlm backed by Groq's chat-completions API.

    `model` carries the bare Groq model id (e.g. "llama-3.3-70b-
    versatile", "openai/gpt-oss-120b"). Non-streaming only: our runtime
    never requests streaming, and a single complete LlmResponse per
    invocation is exactly what ADK's agent loop consumes.
    """

    temperature: float = 0.3

    @classmethod
    def supported_models(cls) -> List[str]:
        return [r"llama-.*", r"openai/gpt-oss-.*", r"meta-llama/.*",
                r"qwen.*", r"groq/.*"]

    async def generate_content_async(
            self, llm_request: LlmRequest,
            stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        messages, tools, max_tokens = translate_request(llm_request)
        payload = await asyncio.to_thread(
            groq_chat, self.model, messages,
            max_tokens=max_tokens, temperature=self.temperature,
            tools=tools or None)
        yield translate_response(payload)


__all__ = ["GroqLlm", "translate_request", "translate_response"]
