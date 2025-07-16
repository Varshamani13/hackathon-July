# agent/github_agent.py

import os
import requests
from openai import OpenAI

# Set up OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Custom function to query MCP server
def call_mcp_tool(input_text):
    try:
        res = requests.post(
            "http://localhost:5001/query",
            headers={"Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"},
            json={"query": input_text},
        )
        return res.json()["response"]
    except Exception as e:
        return f"[MCP Tool Error]: {str(e)}"

# Core "agent" logic using a single LLM call
def build_agent():
    def ask_agent(user_query):
        system_prompt = """
You are a GitHub assistant. When the user asks a question about a GitHub repo,
use the MCP Tool to find the answer. If needed, output the exact query you are sending to MCP.
Then return the result as a helpful answer.

When using MCP Tool, call the function call_mcp_tool() with the query.
"""

        # LLM tries to decide what to do
        completion = openai_client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo" if you prefer
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
        )

        response = completion.choices[0].message.content

        # (Optional) You could parse and detect when tool needs to be called
        if "[MCP_QUERY]" in response:
            query = response.split("[MCP_QUERY]")[1].strip()
            tool_response = call_mcp_tool(query)
            return f"{tool_response}"
        else:
            return response

    return ask_agent
