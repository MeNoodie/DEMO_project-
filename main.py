""" Eco-Friendly App - Main FastAPI Application """

import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import threading
from langchain_core.messages import HumanMessage
from backend.workflow.agents import app as agent_app

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
    requirement: str


@web_app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@web_app.post("/api/analyze")
async def analyze_material(request: MaterialRequest) -> Dict[str, Any]:
    """
    Analyze the construction requirement and return eco-friendly material recommendations.
    """
    try:
        # Create initial state with user message
        initial_state = {
            "messages": [HumanMessage(content=request.requirement)]
        }
        
        # Run the agent graph
        result = agent_app.invoke(initial_state)
        
        # Extract the final report from messages
        messages = result.get("messages", [])
        
        if not messages:
            return {"status": "error", "message": "No results generated"}
        
        # Get the last message (should be the reporter's output)
        final_report = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        
        # Also get research data if available
        research_data = ""
        for msg in messages:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            if hasattr(msg, 'name') and msg.name == "Researcher":
                research_data = content
                break
        
        return {
            "status": "success",
            "requirement": request.requirement,
            "research_data": research_data,
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
