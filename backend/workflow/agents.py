from typing import Annotated , Literal , TypedDict  
from langgraph.types import Command
from langchain_tavily import TavilySearch
from langgraph.graph import MessagesState, END , StateGraph, START ,END
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain_core.tools import Tool
from langchain_groq import ChatGroq

from dotenv import load_dotenv
import os 
import json
load_dotenv()

Tavily_api_key = os.getenv("Tavily_api_key")
search_tool = TavilySearch(
    max_results=5,
    topic="general")

# Load prompts from JSON file
prompts_path = os.path.join(os.path.dirname(__file__), "prompts", "prompts.json")
with open(prompts_path, "r") as f:
    prompts = json.load(f)

researcher_prompt = prompts["researcher_prompt"]
report_prompt = prompts["report_prompt"]
system_prompt_template = prompts["system_prompt"]

members = ['Researcher', 'Reporter', 'FINISH']

# Format the system prompt with members
supervisor_system_prompt = system_prompt_template.format(members=members)

LLM = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal['Researcher', 'Reporter', 'FINISH']


class State(MessagesState):
    next:str

research_agent = create_agent(
    LLM,
    tools = [search_tool],
    system_prompt=researcher_prompt
) 


reporter_agent = create_agent(
    LLM,
    tools = [],
    system_prompt=report_prompt
) 


def supervisor_node(state: State) -> Command[Literal["Researcher", "Reporter", "__end__"]]:
    
    messages = [{"role": "system", "content": supervisor_system_prompt},] + state["messages"]
    
    response = LLM.with_structured_output(Router).invoke(messages)
    
    goto = response["next"]
    
    print("Supervisor initialized")
    
    print(goto)
    
    if goto == "FINISH":
        goto = END
        
    return Command(goto=goto, update={"next": goto})

def Research_node(state: State) -> Command[Literal["supervisor"]]:
    
    result = research_agent.invoke(state)
    
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="Researcher")
            ]
        },
        goto="supervisor",
    )

def Reporter_node(state: State) -> Command[Literal["supervisor"]]:
    
    result = reporter_agent.invoke(state)
    
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="Reporter")
            ]
        },
        goto="supervisor",
    )

graph=StateGraph(State)
graph.add_node("supervisor",supervisor_node)
graph.add_node("Researcher", Research_node)
graph.add_node("Reporter", Reporter_node)

graph.add_edge(START,"supervisor")
# graph.add_edge("supervisor","Researcher")
# graph.add_edge("supervisor","Reporter")
# graph.add_edge("Reporter",END)

app = graph.compile()