"""
Groq provider migration tests (2026-10-01).

AJ's call: Groq is the college MVP's ONLY active LLM provider (Gemini
removed from every college path — its free-tier daily cap kept
exhausting). These tests pin, offline (no network, no real key):

  1. Per-purpose model routing (Groq quotas are per model, so mentor /
     generation / direct / light work draw separate free pools).
  2. The direct-leg wrapper: Groq chat JSON in → `.text` out; HTTP
     429/401/404 map onto the existing LLM_QUOTA / LLM_AUTH /
     LLM_MODEL_NOT_FOUND taxonomy; no key → model is None.
  3. The ADK adapter (college_groq_llm): LlmRequest → Groq messages /
     tools translation (system instruction, function calls, function
     responses, lowercase JSON-schema types) and Groq JSON →
     LlmResponse translation (text, tool calls, usage).
  4. Agent wiring: the mentor hierarchy runs on the mentor pool, the
     one-shot generation twins on the generation pool.
  5. Honest provenance: when the ADK seam is down and only the direct
     Groq leg authors the diagnostic, authored_by is "groq_direct" —
     never the retired "gemini_direct", never an adk:* label.
"""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from google.adk.models.llm_request import LlmRequest
from google.genai import types as genai_types

import backend.core.config as config_mod
import backend.core.gemini as gemini_mod
import backend.core.llm as llm_mod
import backend.services.college_assessment_service as assessment_mod
from backend.agents.college_adk_agents import (
    _llm_available, build_agents, build_generation_agent)
from backend.agents.college_adk_tools import CollegeToolKit
from backend.agents.college_groq_llm import (
    GroqLlm, translate_request, translate_response)
from backend.core.llm import classify_llm_error, model_id_for_purpose
from backend.main import app
from backend.services.college_store import college_store
from college_testkit import install_fake_adapter

client = TestClient(app, raise_server_exceptions=False)
ALICE = {"Authorization": "Bearer " + "alice" + "-token"}


@pytest.fixture(scope="module", autouse=True)
def fake_backend():
    adapter, restore = install_fake_adapter()
    yield adapter
    restore()


@pytest.fixture(autouse=True)
def no_groq_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(config_mod.settings, "GROQ_API_KEY", "",
                        raising=False)


# ---------------------------------------------------------------------------
# 1. Routing
# ---------------------------------------------------------------------------

def test_purpose_routing_uses_separate_groq_pools():
    assert model_id_for_purpose("mentor") == "openai/gpt-oss-120b"
    assert model_id_for_purpose("generation") == "openai/gpt-oss-20b"
    assert model_id_for_purpose("direct") == "openai/gpt-oss-20b"
    assert model_id_for_purpose("light") == "llama-3.1-8b-instant"
    # Unknown purposes fall back to the direct pool, never crash.
    assert model_id_for_purpose("nonsense") == "openai/gpt-oss-20b"
    assert model_id_for_purpose() == "openai/gpt-oss-20b"


def test_no_key_means_no_model_and_agents_unavailable():
    assert gemini_mod.get_gemini_model() is None
    assert gemini_mod.get_gemini_model("light") is None
    assert _llm_available() is False


# ---------------------------------------------------------------------------
# 2. Direct-leg wrapper over a mocked Groq HTTP layer
# ---------------------------------------------------------------------------

def _mock_groq(monkeypatch, handler):
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "Client", factory)
    monkeypatch.setattr(config_mod.settings, "GROQ_API_KEY", "gsk_test",
                        raising=False)


def test_wrapper_round_trip_and_payload(monkeypatch):
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "hello learner"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3,
                      "total_tokens": 13}})

    _mock_groq(monkeypatch, handler)
    model = gemini_mod.get_gemini_model("light")
    assert model is not None
    config = llm_mod.fast_generation_config(123)
    resp = model.generate_content("Say hello", config=config)
    assert resp.text == "hello learner"
    assert captured["model"] == "llama-3.1-8b-instant"
    assert captured["max_tokens"] == 123
    assert captured["messages"] == [
        {"role": "user", "content": "Say hello"}]
    # reasoning_effort is a gpt-oss-only knob; llama must not get it.
    assert "reasoning_effort" not in captured


def test_wrapper_gpt_oss_gets_low_reasoning_effort(monkeypatch):
    """gpt-oss reasoning shares the completion budget; at default
    effort it truncated large structured JSON outputs live. Direct
    legs pin reasoning_effort=low."""
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "[]"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1,
                      "total_tokens": 2}})

    _mock_groq(monkeypatch, handler)
    model = gemini_mod.get_gemini_model("direct")
    model.generate_content("Make a JSON array")
    assert captured["model"] == "openai/gpt-oss-20b"
    assert captured["reasoning_effort"] == "low"


@pytest.mark.parametrize("status,expected", [
    (429, "LLM_QUOTA"), (401, "LLM_AUTH"), (403, "LLM_AUTH"),
    (404, "LLM_MODEL_NOT_FOUND"), (500, "LLM_UNAVAILABLE"),
])
def test_wrapper_error_taxonomy(monkeypatch, status, expected):
    def handler(request):
        return httpx.Response(status, json={
            "error": {"message": "provider said no"}})

    _mock_groq(monkeypatch, handler)
    model = gemini_mod.get_gemini_model()
    with pytest.raises(llm_mod.LLMProviderError) as excinfo:
        model.generate_content("anything")
    assert classify_llm_error(excinfo.value) == expected


# ---------------------------------------------------------------------------
# 3. ADK adapter translation
# ---------------------------------------------------------------------------

def _sample_request() -> LlmRequest:
    fd = genai_types.FunctionDeclaration(
        name="create_assessment", description="Create an assessment",
        parameters=genai_types.Schema(
            type="OBJECT",
            properties={"topic": genai_types.Schema(
                type="STRING", description="Topic title")},
            required=["topic"]))
    config = genai_types.GenerateContentConfig(
        system_instruction="You are the mentor.",
        max_output_tokens=777,
        tools=[genai_types.Tool(function_declarations=[fd])])
    contents = [
        genai_types.Content(role="user", parts=[
            genai_types.Part(text="Assess me on paging")]),
        genai_types.Content(role="model", parts=[
            genai_types.Part(function_call=genai_types.FunctionCall(
                name="create_assessment", args={"topic": "Paging"},
                id="call_1"))]),
        genai_types.Content(role="user", parts=[
            genai_types.Part(function_response=genai_types.FunctionResponse(
                name="create_assessment", response={"ok": True},
                id="call_1"))]),
    ]
    return LlmRequest(model="llama-3.3-70b-versatile",
                      contents=contents, config=config)


def test_translate_request_shape():
    messages, tools, max_tokens = translate_request(_sample_request())
    assert max_tokens == 777
    assert messages[0] == {"role": "system",
                           "content": "You are the mentor."}
    assert messages[1] == {"role": "user",
                           "content": "Assess me on paging"}
    assistant = messages[2]
    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"][0]["id"] == "call_1"
    assert assistant["tool_calls"][0]["function"]["name"] == \
        "create_assessment"
    assert json.loads(
        assistant["tool_calls"][0]["function"]["arguments"]) == \
        {"topic": "Paging"}
    assert messages[3]["role"] == "tool"
    assert messages[3]["tool_call_id"] == "call_1"
    assert json.loads(messages[3]["content"]) == {"ok": True}
    # Schema types are lowercased for the OpenAI-compatible API.
    params = tools[0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"]["topic"]["type"] == "string"
    assert tools[0]["function"]["name"] == "create_assessment"


def test_translate_request_json_schema_flavor():
    """ADK 2.x emits ``parameters_json_schema`` (pydantic flavor), NOT
    ``parameters``. A translator that reads only the classic field
    ships every tool with NO argument schema — the model can see the
    tools but can never call them with arguments. (This is the bug
    that disabled the mentor's whole tool layer in production.)"""
    fd = genai_types.FunctionDeclaration(
        name="create_accountability_commitment",
        description="Create a study commitment",
        parameters_json_schema={
            "type": "object",
            "title": "create_accountability_commitmentParams",
            "properties": {
                "title": {"type": "string", "title": "Title"},
                "topic": {"anyOf": [{"type": "string"},
                                    {"type": "null"}],
                          "default": None, "title": "Topic"},
                "estimated_minutes": {"type": "integer", "default": 60,
                                      "title": "Estimated Minutes"},
            },
            "required": ["title"],
        })
    config = genai_types.GenerateContentConfig(
        tools=[genai_types.Tool(function_declarations=[fd])])
    request = LlmRequest(model="openai/gpt-oss-120b", contents=[],
                         config=config)
    _, tools, _ = translate_request(request)
    params = tools[0]["function"]["parameters"]
    assert params["type"] == "object"
    assert params["properties"]["title"] == {"type": "string"}
    # Optional[X] collapses to X: no anyOf, no null branch, no titles.
    assert params["properties"]["topic"] == {"type": "string"}
    assert params["properties"]["estimated_minutes"] == {"type": "integer"}
    assert params["required"] == ["title"]


def test_translate_request_argless_tool_gets_empty_schema():
    fd = genai_types.FunctionDeclaration(
        name="get_learner_profile", description="Profile")
    config = genai_types.GenerateContentConfig(
        tools=[genai_types.Tool(function_declarations=[fd])])
    request = LlmRequest(model="openai/gpt-oss-120b", contents=[],
                         config=config)
    _, tools, _ = translate_request(request)
    assert tools[0]["function"]["parameters"] == {
        "type": "object", "properties": {}}


def test_real_toolkit_declarations_carry_schemas():
    """Regression test for the live mentor failure: declarations from
    the REAL ADK toolkit (the exact objects production builds) must
    reach the provider WITH argument schemas — above all
    create_accountability_commitment (the mentor's write path) and
    transfer_to_agent (the root's only route to any sub-agent)."""
    from google.adk.tools.transfer_to_agent_tool import (
        TransferToAgentTool)

    kit = CollegeToolKit(college_store)
    agents = build_agents(kit)
    declarations = {}
    for agent in agents.values():
        for tool in (agent.tools or []):
            decl = tool._get_declaration()
            declarations[decl.name] = decl
    declarations["transfer_to_agent"] = TransferToAgentTool(
        agent_names=["accountability"])._get_declaration()
    assert "create_accountability_commitment" in declarations

    fds = [declarations["create_accountability_commitment"],
           declarations["transfer_to_agent"]]
    config = genai_types.GenerateContentConfig(
        tools=[genai_types.Tool(function_declarations=fds)])
    request = LlmRequest(model="openai/gpt-oss-120b", contents=[],
                         config=config)
    _, tools, _ = translate_request(request)
    by_name = {t["function"]["name"]: t["function"] for t in tools}
    commitment = by_name["create_accountability_commitment"]
    props = commitment["parameters"]["properties"]
    assert props["title"]["type"] == "string"
    assert props["due_at"]["type"] == "string"
    assert "title" in commitment["parameters"]["required"]
    assert "due_at" in commitment["parameters"]["required"]
    transfer = by_name["transfer_to_agent"]
    assert transfer["parameters"]["properties"][
        "agent_name"]["type"] == "string"


def test_translate_response_text_and_tool_calls():
    payload = {
        "choices": [{"finish_reason": "tool_calls", "message": {
            "content": "Working on it",
            "tool_calls": [{"id": "call_9", "type": "function",
                            "function": {
                                "name": "get_topic_mastery_state",
                                "arguments": "{\"uid\": \"u1\"}"}}]}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 9,
                  "total_tokens": 59}}
    resp = translate_response(payload)
    parts = resp.content.parts
    assert parts[0].text == "Working on it"
    fc = parts[1].function_call
    assert fc.name == "get_topic_mastery_state"
    assert fc.args == {"uid": "u1"}
    assert fc.id == "call_9"
    assert resp.usage_metadata.total_token_count == 59
    assert resp.turn_complete is True


def test_groq_llm_round_trip(monkeypatch):
    seen = {}

    def fake_chat(model_id, messages, **kwargs):
        seen.update(model=model_id, messages=messages, kwargs=kwargs)
        return {"choices": [{"message": {"content": "Namaste, learner"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2,
                          "total_tokens": 7}}

    import backend.agents.college_groq_llm as groq_llm_mod
    monkeypatch.setattr(groq_llm_mod, "groq_chat", fake_chat)
    llm = GroqLlm(model="openai/gpt-oss-120b")

    async def collect():
        return [ev async for ev in llm.generate_content_async(
            _sample_request())]

    events = asyncio.run(collect())
    assert len(events) == 1
    assert events[0].content.parts[0].text == "Namaste, learner"
    assert seen["model"] == "openai/gpt-oss-120b"
    assert seen["kwargs"]["max_tokens"] == 777
    assert seen["kwargs"]["tools"], "tools must reach the provider call"
    assert seen["kwargs"]["reasoning_effort"] == "low"


# ---------------------------------------------------------------------------
# 4. Agent wiring
# ---------------------------------------------------------------------------

def test_agents_run_on_groq_pools():
    kit = CollegeToolKit(college_store)
    agents = build_agents(kit)
    for agent in agents.values():
        assert isinstance(agent.model, GroqLlm)
        assert agent.model.model == config_mod.settings.GROQ_MODEL_MENTOR
    for key in ("assessment", "plan"):
        twin = build_generation_agent(key)
        assert isinstance(twin.model, GroqLlm)
        assert twin.model.model == \
            config_mod.settings.GROQ_MODEL_GENERATION


# ---------------------------------------------------------------------------
# 5. Provenance: the direct leg is labeled groq_direct, nothing else
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, text):
        self.text = text


_DIAGNOSTIC = [
    {"id": "dq1", "text": "What is the time complexity of head "
     "insertion in a singly linked list?", "type": "MCQ",
     "options": ["O(1)", "O(n)", "O(log n)", "O(n log n)"],
     "answer": "A", "topic": "Linked Lists", "marks": 5,
     "probe": "concept", "source": "verified_curriculum"},
    {"id": "dq2", "text": "Which scheduling algorithm can cause "
     "starvation?", "type": "MCQ",
     "options": ["Round Robin", "SJF", "FCFS", "Multilevel"],
     "answer": "B", "topic": "Scheduling", "marks": 5,
     "probe": "concept", "source": "verified_curriculum"},
    {"id": "dq3", "text": "In paging, a page fault occurs when?",
     "type": "MCQ",
     "options": ["Page in RAM", "Page not in RAM", "TLB hit",
                 "Cache miss"],
     "answer": "B", "topic": "Paging", "marks": 5,
     "probe": "misconception", "source": "model_generated"},
    {"id": "dq4", "text": "Explain why arrays give O(1) random access "
     "but linked lists do not.", "type": "SHORT_ANSWER",
     "rubric": "Contiguous memory + index arithmetic vs pointer "
     "traversal", "topic": "Arrays", "marks": 5, "probe": "concept",
     "source": "verified_curriculum"},
    {"id": "dq5", "text": "Describe how virtual memory lets processes "
     "exceed physical RAM.", "type": "SHORT_ANSWER",
     "rubric": "Pages swapped between disk and RAM on demand",
     "topic": "Virtual Memory", "marks": 5, "probe": "application",
     "source": "model_generated"},
]


class _DirectModel:
    def generate_content(self, prompt):
        return _Resp(json.dumps(_DIAGNOSTIC))


async def _adk_down(agent_key, prompt, **kwargs):
    raise RuntimeError("ADK unavailable in tests")


def test_diagnostic_direct_leg_stamps_groq_direct(monkeypatch):
    r = client.post("/api/college/profile",
                    json={"name": "Alice",
                          "email": "alice@example.com"}, headers=ALICE)
    assert r.status_code == 200, r.text
    r = client.post("/api/college/academic-context", json={
        "university_id": "univ_aicte_model",
        "branch": "COMPUTER_SCIENCE_ENGINEER",
        "semester": 3, "subjects": ["CS-301", "CS-302"],
        "available_hours_per_week": 10,
    }, headers=ALICE)
    assert r.status_code == 200, r.text

    monkeypatch.setattr(assessment_mod, "run_agent_generation", _adk_down)
    monkeypatch.setattr(gemini_mod, "get_gemini_model",
                        lambda *a, **k: _DirectModel())
    r = client.post("/api/college/assessments/diagnostic", json={},
                    headers=ALICE)
    assert r.status_code == 200, r.text
    assert r.json()["authored_by"] == "groq_direct"
