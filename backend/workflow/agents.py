from __future__ import annotations

from typing import Any, Dict
from langgraph.types import Command
from langchain_tavily import TavilySearch
from langgraph.graph import MessagesState, END, StateGraph, START
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import json
import re

from backend.workflow.rag import get_rag_system

load_dotenv()

search_tool = TavilySearch(max_results=5, topic="general")

prompts_path = os.path.join(os.path.dirname(__file__), "prompts", "prompts.json")


def _safe_json_unescape(raw: str) -> str:
    try:
        return json.loads(f"\"{raw}\"")
    except Exception:
        return raw


def _load_prompts(path: str) -> Dict[str, str]:
    raw_text = ""
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    try:
        parsed = json.loads(raw_text)
        return {
            "researcher_prompt": parsed.get("researcher_prompt", ""),
            "report_prompt": parsed.get("report_prompt", ""),
            "system_prompt": parsed.get("system_prompt", ""),
        }
    except json.JSONDecodeError:
        # Fallback parser to keep compatibility with a non-JSON report_prompt
        # stored as a triple-quoted block in prompts.json.
        researcher_match = re.search(
            r'"researcher_prompt"\s*:\s*"(?P<value>.*?)"\s*,\s*"report_prompt"',
            raw_text,
            re.DOTALL,
        )
        report_match = re.search(
            r'"report_prompt"\s*:\s*"""(?P<value>.*?)"""\s*,\s*"system_prompt"',
            raw_text,
            re.DOTALL,
        )
        system_match = re.search(
            r'"system_prompt"\s*:\s*"(?P<value>.*?)"\s*}\s*$',
            raw_text,
            re.DOTALL,
        )

        if not researcher_match or not report_match:
            raise ValueError("Unable to parse prompts from prompts.json.")

        researcher_prompt = _safe_json_unescape(researcher_match.group("value"))
        report_prompt = report_match.group("value").strip()
        system_prompt = _safe_json_unescape(system_match.group("value")) if system_match else ""

        return {
            "researcher_prompt": researcher_prompt,
            "report_prompt": report_prompt,
            "system_prompt": system_prompt,
        }


prompts = _load_prompts(prompts_path)

researcher_prompt = prompts["researcher_prompt"]
report_prompt = prompts["report_prompt"]

LLM = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)


class State(MessagesState):
    user_input: Dict[str, Any]
    engineering_measures: Dict[str, Any]
    requirement: str
    research_query: str
    rag_research: str
    web_research: str
    combined_research: str
    final_report: str
    visual_data: Dict[str, Any]


research_agent = create_agent(
    LLM,
    tools=[search_tool],
    system_prompt=researcher_prompt,
)

reporter_agent = create_agent(
    LLM,
    tools=[],
    system_prompt=report_prompt,
)

coding_agent = create_agent(
    LLM,
    tools=[],
    system_prompt=(
        "You are a coding analyst that converts engineering decisions into frontend-ready JSON charts. "
        "Return only valid JSON and nothing else."
    ),
)


def _extract_json_object(text: str) -> Dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def _normalized_score(raw_value: float, raw_min: float = 0.0, raw_max: float = 10.0) -> float:
    if raw_max <= raw_min:
        return 0.0
    clamped = max(raw_min, min(raw_max, raw_value))
    return round(((clamped - raw_min) / (raw_max - raw_min)) * 100, 2)


def _fallback_visual_data(state: State) -> Dict[str, Any]:
    engineering = state.get("engineering_measures", {})
    weights = {
        "thermal": float(engineering.get("thermal_weight", 0.3)),
        "cost": float(engineering.get("cost_weight", 0.3)),
        "sustainability": float(engineering.get("sustainability_weight", 0.4)),
    }

    structural = float(engineering.get("structural_requirement", 5))
    cost = float(engineering.get("cost_sensitivity", 5))
    rainfall = float(engineering.get("rainfall_risk", 5))
    speed = float(engineering.get("speed_requirement", 5))

    materials = [
        {
            "name": "Compressed Stabilized Earth Blocks",
            "strength": _normalized_score((structural * 0.75) + 1.2),
            "thermal": _normalized_score((rainfall * 0.5) + 2.5),
            "sustainability": _normalized_score(8.8),
            "cost": _normalized_score((cost * 0.9) + 0.8),
            "risk": _normalized_score((speed * 0.6) + (rainfall * 0.2)),
        },
        {
            "name": "AAC Block System",
            "strength": _normalized_score((structural * 0.85) + 1.0),
            "thermal": _normalized_score(8.1),
            "sustainability": _normalized_score(7.1),
            "cost": _normalized_score((cost * 0.7) + 1.5),
            "risk": _normalized_score((rainfall * 0.7) + 1.3),
        },
        {
            "name": "Fly-Ash Brick + Insulation",
            "strength": _normalized_score((structural * 0.8) + 1.4),
            "thermal": _normalized_score((rainfall * 0.4) + 3.2),
            "sustainability": _normalized_score(7.8),
            "cost": _normalized_score((cost * 0.8) + 1.1),
            "risk": _normalized_score((speed * 0.5) + (rainfall * 0.3)),
        },
    ]

    for material in materials:
        weighted_score = (
            material["thermal"] * weights["thermal"]
            + material["cost"] * weights["cost"]
            + material["sustainability"] * weights["sustainability"]
        )
        material["score"] = round(weighted_score, 2)

    materials = sorted(materials, key=lambda x: x["score"], reverse=True)

    return {
        "material_scores": materials,
        "priority_mix": {
            "thermal": round(weights["thermal"] * 100, 2),
            "cost": round(weights["cost"] * 100, 2),
            "sustainability": round(weights["sustainability"] * 100, 2),
        },
        "project_risk": {
            "climate_risk": _normalized_score(rainfall),
            "cost_pressure": _normalized_score(10 - cost),
            "delivery_pressure": _normalized_score(speed),
        },
        "highlights": [
            "Scores are aligned to engineering weights and project constraints.",
            "Higher score indicates stronger fit for this project profile.",
            "Risk bars show pressure points to mitigate in implementation planning.",
        ],
    }


def research_node(state: State) -> Command[str]:
    requirement = state.get("requirement", "")
    research_query = state.get("research_query", requirement)
    user_input = state.get("user_input", {})
    engineering = state.get("engineering_measures", {})

    project_context = json.dumps(
        {
            "user_input": user_input,
            "engineering_measures": engineering,
        },
        ensure_ascii=True,
        indent=2,
    )

    rag_text = "RAG unavailable."
    try:
        rag_result = get_rag_system().ask(research_query, project_context=project_context)
        rag_text = rag_result.get("answer", "RAG returned no answer.")
    except Exception as exc:
        rag_text = f"RAG lookup failed: {exc}"

    web_text = "Web research unavailable."
    try:
        research_request = (
            "Collect recent and practical engineering/sustainability evidence for this project.\n"
            f"Project requirement: {requirement}\n"
            f"Merged retrieval query:\n{research_query}\n"
            f"Project context:\n{project_context}\n"
            "Include material options, climate suitability, durability, cost/availability signals, and standards where possible."
        )
        result = research_agent.invoke({"messages": [HumanMessage(content=research_request)]})
        web_text = result["messages"][-1].content
    except Exception as exc:
        web_text = f"Web research failed: {exc}"

    combined = (
        "## RAG Research\n"
        f"{rag_text}\n\n"
        "## Web Research\n"
        f"{web_text}"
    )

    return Command(
        update={
            "rag_research": rag_text,
            "web_research": web_text,
            "combined_research": combined,
            "messages": [HumanMessage(content=combined, name="Researcher")],
        },
        goto="Reporter",
    )


def reporter_node(state: State) -> Command[str]:
    user_input = state.get("user_input", {})
    engineering = state.get("engineering_measures", {})
    combined_research = state.get("combined_research", "")
    requirement = state.get("requirement", "")
    research_query = state.get("research_query", requirement)

    report_request = (
        "Create the final markdown report.\n"
        f"User requirement:\n{requirement}\n\n"
        f"Merged retrieval query used for research:\n{research_query}\n\n"
        f"Structured user inputs:\n{json.dumps(user_input, ensure_ascii=True, indent=2)}\n\n"
        f"Engineering calculations and measures:\n{json.dumps(engineering, ensure_ascii=True, indent=2)}\n\n"
        f"Research bundle (RAG + web):\n{combined_research}\n"
    )

    result = reporter_agent.invoke({"messages": [HumanMessage(content=report_request)]})
    final_report = result["messages"][-1].content

    return Command(
        update={
            "final_report": final_report,
            "messages": [HumanMessage(content=final_report, name="Reporter")],
        },
        goto="CodingAnalyst",
    )


def coding_analyst_node(state: State) -> Command[str]:
    engineering = state.get("engineering_measures", {})
    report = state.get("final_report", "")

    coder_request = (
        "Create chart data for frontend rendering in strict JSON format.\n"
        "Schema:\n"
        "{\n"
        '  "material_scores": [{"name": str, "strength": number, "thermal": number, '
        '"sustainability": number, "cost": number, "risk": number, "score": number}],\n'
        '  "priority_mix": {"thermal": number, "cost": number, "sustainability": number},\n'
        '  "project_risk": {"climate_risk": number, "cost_pressure": number, "delivery_pressure": number},\n'
        '  "highlights": [str]\n'
        "}\n"
        "Rules:\n"
        "- number range must be 0-100\n"
        "- include exactly 3 materials\n"
        "- use project metrics and report context\n"
        "- output valid JSON only\n\n"
        f"Engineering metrics:\n{json.dumps(engineering, ensure_ascii=True, indent=2)}\n\n"
        f"Final report context:\n{report}\n"
    )

    visual_data = None
    try:
        result = coding_agent.invoke({"messages": [HumanMessage(content=coder_request)]})
        text = result["messages"][-1].content
        visual_data = _extract_json_object(text)
    except Exception:
        visual_data = None

    if not visual_data:
        visual_data = _fallback_visual_data(state)

    return Command(
        update={
            "visual_data": visual_data,
            "messages": [HumanMessage(content=json.dumps(visual_data), name="CodingAnalyst")],
        },
        goto=END,
    )

graph = StateGraph(State)
graph.add_node("Researcher", research_node)
graph.add_node("Reporter", reporter_node)
graph.add_node("CodingAnalyst", coding_analyst_node)
graph.add_edge(START, "Researcher")
graph.add_edge("CodingAnalyst", END)

app = graph.compile()
