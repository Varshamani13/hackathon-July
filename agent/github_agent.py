# agent/github_agent.py

import os
from openai import AssistantEventHandler, OpenAI
from openai.agents import Agent, Tool

# MCP Tool Setup (communicates with GitHub MCP server)
class MCPTool(Tool):
    def call(self, input_text):
        # Send POST to your locally running MCP server
        import requests
        res = requests.post(
            "http://localhost:5001/query",  # Example port
            headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
            json={"query": input_text},
        )
        return res.json()["response"]

def build_agent():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    tools = [MCPTool(name="mcp_tool", description="Tool for analyzing GitHub repos")]
    
    agent = Agent(
        client=openai_client,
        instructions="You are a GitHub assistant. Use the MCP tool to answer repository questions.",
        tools=tools
    )
    return agent
