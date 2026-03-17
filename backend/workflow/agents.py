from typing import Any, Dict, TypedDict
from langgraph.types import Command
from langchain_tavily import TavilySearch
from langgraph.graph import MessagesState, END, StateGraph, START
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import json

from backend.workflow.rag import get_rag_system

load_dotenv()

search_tool = TavilySearch(max_results=5, topic="general")

prompts_path = os.path.join(os.path.dirname(__file__), "prompts", "prompts.json")
with open(prompts_path, "r", encoding="utf-8") as f:
    prompts = json.load(f)

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
        goto=END,
    )

graph = StateGraph(State)
graph.add_node("Researcher", research_node)
graph.add_node("Reporter", reporter_node)
graph.add_edge(START, "Researcher")
graph.add_edge("Reporter", END)

app = graph.compile()
