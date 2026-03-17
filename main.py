""" Eco-Friendly App - Main FastAPI Application """

import os
import json
import re
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from langchain_core.messages import HumanMessage
from backend.workflow.agents import app as agent_app
from backend.workflow.material_feature import compute_project_requirements

# Load environment variables
load_dotenv()

web_app = FastAPI(title="Eco-Friendly Material Advisor", description="AI-powered sustainable material recommendations")

# Add CORS middleware
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


templates = Jinja2Templates(directory="frontend/templates")
web_app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


# Request model
class MaterialRequest(BaseModel):
    requirement: Optional[str] = None
    building_type: Optional[str] = None
    floors: Optional[int] = None
    location: Optional[str] = None
    budget_level: Optional[str] = None
    priority: Optional[str] = None
    rainfall: Optional[str] = None
    material_tone: Optional[str] = None
    timeline: Optional[str] = None
    cost_preference: Optional[str] = None
    notes: Optional[str] = None


def build_research_query(user_input: Dict[str, Any], engineering_measures: Dict[str, Any]) -> str:
    indices = engineering_measures.get("engineering_indices", {})
    tradeoff = engineering_measures.get("tradeoff_adjustment", {})

    return (
        "Eco-friendly construction material retrieval query:\n"
        f"- Building type: {user_input.get('building_type', 'unknown')}\n"
        f"- Floors: {user_input.get('floors', 'unknown')}\n"
        f"- Location: {user_input.get('location', 'unknown')}\n"
        f"- Budget: {user_input.get('budget_level', 'moderate')}\n"
        f"- Main priority: {user_input.get('priority', 'cooling')}\n"
        f"- Rainfall exposure: {user_input.get('rainfall', 'medium')}\n"
        f"- Material tone: {user_input.get('material_tone', 'balanced')}\n"
        f"- Timeline: {user_input.get('timeline', 'standard')}\n"
        f"- Tradeoff focus: {user_input.get('cost_preference', 'balanced')}\n"
        f"- Notes: {user_input.get('notes', '')}\n"
        "\nEngineering calculation summary:\n"
        f"- Structural requirement score: {engineering_measures.get('structural_requirement')}\n"
        f"- Cost sensitivity score: {engineering_measures.get('cost_sensitivity')}\n"
        f"- Rainfall risk score: {engineering_measures.get('rainfall_risk')}\n"
        f"- Speed requirement score: {engineering_measures.get('speed_requirement')}\n"
        f"- Thermal weight: {engineering_measures.get('thermal_weight')}\n"
        f"- Cost weight: {engineering_measures.get('cost_weight')}\n"
        f"- Sustainability weight: {engineering_measures.get('sustainability_weight')}\n"
        f"- Climate class: {engineering_measures.get('climate')}\n"
        f"- Tradeoff adjustment: {tradeoff}\n"
        f"- Engineering indices: {indices}\n"
        "\nRequired retrieval target:\n"
        "Find the best-fit eco-friendly material options with technical properties, durability in local climate, "
        "cost/availability signals, and implementation constraints. Include practical comparison against conventional materials."
    )


def extract_top_retrieval_terms(research_query: str, top_k: int = 3) -> list[str]:
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "into", "your", "user",
        "project", "query", "summary", "score", "find", "best", "fit", "options",
        "materials", "material", "include", "against", "where", "possible", "unknown",
        "notes", "budget", "type", "main", "focus", "required", "target", "engineering",
        "calculation", "calculations", "retrieval", "eco", "friendly", "construction",
    }

    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", research_query.lower())
    frequencies: Dict[str, int] = {}
    for word in words:
        if word in stop_words:
            continue
        frequencies[word] = frequencies.get(word, 0) + 1

    ranked = sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ranked[:top_k]]


@web_app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@web_app.post("/api/analyze")
async def analyze_material(request: MaterialRequest) -> Dict[str, Any]:
    """
    Analyze the construction requirement and return eco-friendly material recommendations.
    """
    try:
        user_input = request.model_dump()

        if not user_input.get("requirement"):
            user_input["requirement"] = (
                f"Recommend eco-friendly materials for a {user_input.get('building_type', 'building')} "
                f"project in {user_input.get('location', 'unspecified location')} with "
                f"{user_input.get('floors', 1)} floors, {user_input.get('budget_level', 'moderate')} budget, "
                f"priority {user_input.get('priority', 'cooling')}, rainfall {user_input.get('rainfall', 'medium')}, "
                f"timeline {user_input.get('timeline', 'standard')}."
            )

        engineering_measures = compute_project_requirements(user_input)
        research_query = build_research_query(user_input, engineering_measures)
        top_retrieval_terms = extract_top_retrieval_terms(research_query, top_k=3)

        # Create initial state with user message
        initial_state = {
            "messages": [HumanMessage(content=user_input["requirement"])],
            "requirement": user_input["requirement"],
            "research_query": research_query,
            "user_input": user_input,
            "engineering_measures": engineering_measures,
        }
        
        # Run the agent graph
        result = agent_app.invoke(initial_state)

        final_report = result.get("final_report", "")
        if not final_report:
            messages = result.get("messages", [])
            for message in reversed(messages):
                name = getattr(message, "name", "")
                if name == "Reporter" and hasattr(message, "content"):
                    final_report = message.content
                    break

        if not final_report:
            return {"status": "error", "message": "No final report generated"}

        research_data = result.get("combined_research", "")
        rag_data = result.get("rag_research", "")
        web_data = result.get("web_research", "")
        visual_data = result.get("visual_data", {})
        
        return {
            "status": "success",
            "requirement": user_input["requirement"],
            "user_input": user_input,
            "engineering_measures": engineering_measures,
            "research_query": research_query,
            "retrieval_debug": {
                "top_terms": top_retrieval_terms,
                "query_preview": research_query,
            },
            "research_data": research_data,
            "rag_data": rag_data,
            "web_data": web_data,
            "visual_data": visual_data,
            "report": final_report
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(web_app, host="0.0.0.0", port=8000)
