"""
ADK agent definitions for the PathMind College MVP (TRD §4).

One learner-facing root agent with six specialized sub-agents. The root
orchestrates; deterministic services (wrapped as FunctionTools) enforce
product rules. The LLM never computes scores, streaks, unlocks, or auth —
it reasons, explains, and delegates to tools.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

try:
    from google.adk.agents import LlmAgent
    _ADK_IMPORT_OK = True
except ImportError:  # pragma: no cover - envs without a working google.adk
    # google-adk shares the `google` namespace with google-cloud-*; a broken
    # namespace must degrade to the legacy orchestrator, never crash boot.
    LlmAgent = None  # type: ignore[assignment]
    _ADK_IMPORT_OK = False

from backend.agents.college_adk_tools import CollegeToolKit
from backend.core.config import settings


def _agent_model(model_id: str):
    """
    Build the ADK model for a Groq model id. The college MVP's only
    provider is Groq (AJ's call, 2026-10-01), reached through our own
    BaseLlm adapter — see backend.agents.college_groq_llm for why we
    don't take the LiteLLM dependency. Constructed per agent so no
    instance is shared across the hierarchy.
    """
    from backend.agents.college_groq_llm import GroqLlm
    return GroqLlm(model=model_id)


def _fast_agent_config(max_output_tokens: int = 2048):
    """
    Bounded generation config shared by every college agent (see
    backend.core.llm.fast_generation_config): output capped so one
    generation cannot starve chained flows inside the 60s serverless
    window. (The thinking-off field is a Gemini-era knob; the Groq
    adapter simply reads the cap.) Returns None when the config cannot
    be built — agents then run with SDK defaults, exactly as before.
    """
    try:
        from backend.core.llm import fast_generation_config
        return fast_generation_config(max_output_tokens)
    except Exception:
        return None

# Instruction strings shared by the tool-wired sub-agents (build_agents)
# and their tool-less one-shot generation twins (build_generation_agent),
# so a one-shot generation runs under the SAME name/instruction/model as
# the conversational sub-agent — only the tools differ (none: generation
# must produce text, never act).
PLAN_AGENT_INSTRUCTION = (
    "You are the Study-Plan sub-agent. Build ordered multi-phase "
    "learning plans via create_study_plan, attach verified resources "
    "via get_verified_resources, and mark progress via update_progress. "
    "Phase unlocks are mastery-gated by deterministic rules — you do "
    "not unlock phases yourself. If resources are not yet verified "
    "(RESOURCE_ENRICHMENT_PENDING), run trigger_resource_research with "
    "a small budget (<=30s) and tell the learner enrichment is "
    "in progress rather than showing unverified links."
)

ASSESSMENT_AGENT_INSTRUCTION = (
    "You are the Assessment sub-agent. Before authoring, read "
    "get_topic_mastery_state and select the learner's weakest topics "
    "first (adaptive selection). Create checkpoint or diagnostic "
    "assessments with create_assessment and grade submissions with "
    "evaluate_assessment. Record weaknesses as learning signals via "
    "record_learning_signal. You never compute scores by hand — "
    "the tools do. Question IDs and responses are stored by the tools. "
    "When authoring a diagnostic: prefer adapting real past-year "
    "questions (PYQs) over inventing textbook-style ones, order "
    "questions easiest first, spread them across units like the real "
    "paper, and keep the tone zero-stakes — it is an exam-readiness "
    "check, never a pass/fail test."
)


def _response_contract() -> str:
    return """
RESPONSE CONTRACT — every reply MUST be exactly one JSON object, no prose
outside it:

{
  "message": "<2-6 sentence mentor reply to the learner>",
  "state": "<ONE of: ONBOARDING | LEARNING | ASSESSMENT | PYQ_REVIEW | PLAN_REVIEW | ACCOUNTABILITY | NEEDS_CONTEXT>",
  "ui_blocks": [ ... ],
  "sources": [ ... ]
}

ui_blocks entries:
  {"type": "LEARNING_PLAN", "data": {"subject": "...", "steps": [{"title": "...", "activity_type": "...", "status": "...", "instructions": "..."}]}}
  {"type": "RESOURCE_LIST", "data": {"resources": [{"title": "...", "url": "...", "resource_type": "...", "tier": "...", "timestamps": [...] }]}}
  {"type": "PYQ_VIEW", "data": <pyq tool result>}
  {"type": "NEXT_ACTION", "data": {"label": "...", "action": "..."}}
  {"type": "ASSESSMENT_PROMPT", "data": <assessment tool result>}
  {"type": "TEXT", "data": {"text": "..."}}

sources: list of URL strings that were VERIFIED by a tool (VERIFIED status).
Never invent a URL. Never list an unverified link. If the tools returned no
verified sources, "sources" MUST be [].

HONESTY RULES (non-negotiable):
- Use only tool results for facts: plans, resources, PYQs, mastery, streaks.
- If a tool returns PYQ_NOT_AVAILABLE / CURRICULUM_NOT_FOUND /
  RESOURCE_ENRICHMENT_PENDING / NEEDS_CONTEXT, say so plainly to the learner
  and pick the matching state. Never claim unverified material is verified.
- Memory tool results are the learner's memory. Never invent preferences.
- Video timestamps: only show chapters from the resource's timestamps field;
  if a timestamp entry is labeled "estimated", say it is estimated.
"""


def _llm_available() -> bool:
    """True when ADK is importable and a Groq key is configured."""
    return _ADK_IMPORT_OK and bool(
        settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY"))


# Legacy name (the provider was Gemini until 2026-10-01); the runtime
# and older imports bind to it.
_gemini_available = _llm_available


def build_agents(toolkit: CollegeToolKit,
                 context_brief: Optional[str] = None) -> Dict[str, LlmAgent]:
    """
    Construct the root agent + six sub-agents bound to the given tool kit.

    context_brief: short text with recent chat history + memory summaries,
    injected into the root instruction so the agent actually remembers.

    Raises RuntimeError when google-adk is not importable; callers are
    expected to catch this and use the deterministic legacy orchestrator.
    """
    if not _ADK_IMPORT_OK or LlmAgent is None:
        raise RuntimeError("google-adk is not importable in this environment")
    agent_config = _fast_agent_config()
    academic = LlmAgent(
        name="academic_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=(
            "You are the Academic sub-agent for a college engineering mentor. "
            "Maintain the learner's academic context: profile, subjects, "
            "active goal, verified university curriculum. Use your tools to "
            "resolve universities and curricula. If the curriculum is not "
            "found, say so honestly — never invent a syllabus. Always return "
            "your findings as compact JSON the root agent can relay."
        ),
        tools=toolkit.as_function_tools([
            "get_learner_profile", "get_academic_context",
            "get_current_subjects", "get_active_goal",
            "search_university_sources", "get_verified_curriculum",
        ]),
    )

    plan = LlmAgent(
        name="plan_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=PLAN_AGENT_INSTRUCTION,
        tools=toolkit.as_function_tools([
            "get_academic_context", "get_current_subjects",
            "get_verified_curriculum", "get_verified_resources",
            "trigger_resource_research", "create_study_plan", "update_progress",
        ]),
    )

    assessment = LlmAgent(
        name="assessment_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=ASSESSMENT_AGENT_INSTRUCTION,
        tools=toolkit.as_function_tools([
            "get_topic_mastery_state", "create_assessment",
            "evaluate_assessment", "record_learning_signal",
        ]),
    )

    accountability = LlmAgent(
        name="accountability_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=(
            "You are the Accountability sub-agent. Create commitments with "
            "create_accountability_commitment and report today's state with "
            "get_accountability_state (deterministic exam countdown, honest "
            "streaks — zero means zero). Never mark anything completed without "
            "evidence; completion flows through update_progress."
        ),
        tools=toolkit.as_function_tools([
            "create_accountability_commitment", "get_accountability_state",
            "update_progress",
        ]),
    )

    memory = LlmAgent(
        name="memory_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=(
            "You are the Memory sub-agent. Maintain the learner model: read "
            "short/long-term memory before other agents act, update the "
            "per-topic mastery picture via record_learning_signal when "
            "learning signals arrive, and persist only stable, useful, "
            "future-relevant observations via record_memory (TRD §19 write "
            "policy). Never invent memories or preferences."
        ),
        tools=toolkit.as_function_tools([
            "retrieve_short_term_memory", "retrieve_long_term_memory",
            "record_memory", "record_learning_signal",
            "get_topic_mastery_state", "get_learner_profile",
        ]),
    )

    pyq = LlmAgent(
        name="pyq_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=(
            "You are the PYQ sub-agent. Retrieve verified previous-year "
            "questions with get_verified_pyqs only. If the result is "
            "PYQ_NOT_AVAILABLE, report that honestly and suggest studying "
            "from the verified resources instead. NEVER invent exam questions."
        ),
        tools=toolkit.as_function_tools([
            "get_verified_pyqs", "get_verified_resources",
            "get_academic_context", "get_current_subjects",
        ]),
    )

    subagents: List[LlmAgent] = [academic, plan, assessment,
                                 accountability, memory, pyq]

    root_instruction = (
        "You are PATHMIND, an expert engineering-college academic mentor for "
        "Indian engineering students. You orchestrate six specialist "
        "sub-agents: academic_agent (context/curriculum), plan_agent "
        "(study plans/resources), assessment_agent (diagnostics/checkpoints), "
        "accountability_agent (commitments/streaks), memory_agent (learner "
        "model — consult it BEFORE acting on preferences or weaknesses), and "
        "pyq_agent (verified previous-year questions). Delegate to the right "
        "sub-agent; do not do their work yourself. "
        "Deterministic facts (scores, streaks, countdowns, unlocks) come "
        "only from tool results — never compute or guess them. "
        "Ask the memory_agent for the learner model early in the turn."
        + _response_contract()
    )
    if context_brief:
        root_instruction += (
            "\n\nCONVERSATION CONTEXT (from persisted chat history and "
            f"memory — this is what you remember):\n{context_brief}"
        )

    root = LlmAgent(
        name="college_root_agent",
        model=_agent_model(settings.GROQ_MODEL_MENTOR),
        generate_content_config=agent_config,
        instruction=root_instruction,
        sub_agents=subagents,
        tools=toolkit.as_function_tools([
            "get_learner_profile", "retrieve_short_term_memory",
            "retrieve_long_term_memory", "get_topic_mastery_state",
        ]),
    )
    return {
        "root": root,
        "academic": academic, "plan": plan, "assessment": assessment,
        "accountability": accountability, "memory": memory, "pyq": pyq,
    }


_GENERATION_AGENT_SPECS = {
    "plan": ("plan_agent", PLAN_AGENT_INSTRUCTION),
    "assessment": ("assessment_agent", ASSESSMENT_AGENT_INSTRUCTION),
}


def build_generation_agent(agent_key: str) -> LlmAgent:
    """
    Tool-less one-shot generation twin of a named sub-agent.

    Same name, instruction, and model as the tool-wired sub-agent built
    by build_agents, but with NO tools: it exists to author text in a
    single bounded Runner turn (diagnostic questions, plan
    personalization), never to act on the store. Services run it via
    college_adk_runtime.run_agent_generation and validate its output
    with the same deterministic validators as any other model output.

    Raises RuntimeError when google-adk is not importable (callers fall
    back honestly) and ValueError for an unknown agent_key.
    """
    if not _ADK_IMPORT_OK or LlmAgent is None:
        raise RuntimeError("google-adk is not importable in this environment")
    try:
        name, instruction = _GENERATION_AGENT_SPECS[agent_key]
    except KeyError:
        raise ValueError(f"unknown generation agent: {agent_key!r}")
    # Per-agent output caps: the assessment author returns a full
    # 5-6 question JSON set (a 2048 cap risks truncating the tail
    # question mid-object, which fails the whole parse); the plan
    # personalizer returns one small object per phase.
    caps = {"assessment": 4096, "plan": 3072}
    return LlmAgent(
        name=name,
        model=_agent_model(settings.GROQ_MODEL_GENERATION),
        instruction=instruction,
        generate_content_config=_fast_agent_config(
            caps.get(agent_key, 2048)),
        tools=[],
    )


__all__ = ["build_agents", "build_generation_agent", "CollegeToolKit",
           "_gemini_available", "_llm_available", "PLAN_AGENT_INSTRUCTION",
           "ASSESSMENT_AGENT_INSTRUCTION"]
