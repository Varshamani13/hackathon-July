import streamlit as st
import asyncio
import json
import os
from typing import Dict, List, Any, Optional
import subprocess
import time
from dataclasses import dataclass
from openai import OpenAI
import requests
from datetime import datetime

@dataclass
class MCPResponse:
    """Structure for MCP server responses"""
    success: bool
    data: Any
    error: Optional[str] = None

class MCPClient:
    """Client for communicating with MCP server"""
    
    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url
        self.session = requests.Session()
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        """Call a tool on the MCP server"""
        try:
            response = self.session.post(
                f"{self.server_url}/tools/{tool_name}",
                json={"arguments": arguments},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return MCPResponse(success=True, data=data)
            else:
                return MCPResponse(
                    success=False, 
                    data=None, 
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return MCPResponse(success=False, data=None, error=str(e))
    
    def list_tools(self) -> MCPResponse:
        """List available tools from MCP server"""
        try:
            response = self.session.get(f"{self.server_url}/tools")
            if response.status_code == 200:
                return MCPResponse(success=True, data=response.json())
            else:
                return MCPResponse(success=False, data=None, error=f"HTTP {response.status_code}")
        except Exception as e:
            return MCPResponse(success=False, data=None, error=str(e))

class GitHubAgent:
    """AI Agent for GitHub repository analysis"""
    
    def __init__(self, openai_api_key: str, github_token: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.github_token = github_token
        self.mcp_client = MCPClient()
        
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze user query and determine required actions"""
        system_prompt = """You are an AI agent that analyzes GitHub repositories using MCP tools.
        
        Available MCP tools:
        - get_repository_info: Get basic repository information
        - list_issues: Get repository issues
        - get_file_contents: Read file contents
        - search_files: Search for files by name or pattern
        - get_commits: Get recent commits
        - search_code: Search for code content
        
        Based on the user query, determine:
        1. Which MCP tools to use
        2. What arguments to pass to each tool
        3. How to process and present the results
        
        Return a JSON object with:
        {
            "tools_to_use": [{"tool": "tool_name", "arguments": {...}}],
            "processing_strategy": "description of how to handle results",
            "response_format": "how to format the final response"
        }
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "tools_to_use": [],
                "processing_strategy": "error",
                "response_format": f"Error analyzing query: {str(e)}"
            }
    
    def execute_tools(self, tools_to_use: List[Dict]) -> List[MCPResponse]:
        """Execute the required MCP tools"""
        results = []
        
        for tool_config in tools_to_use:
            tool_name = tool_config["tool"]
            arguments = tool_config["arguments"]
            
            st.write(f"🔧 Executing tool: {tool_name}")
            result = self.mcp_client.call_tool(tool_name, arguments)
            results.append(result)
            
            if result.success:
                st.success(f"✅ Tool {tool_name} executed successfully")
            else:
                st.error(f"❌ Tool {tool_name} failed: {result.error}")
        
        return results
    
    def generate_response(self, query: str, tool_results: List[MCPResponse], processing_strategy: str) -> str:
        """Generate final response based on tool results"""
        
        # Prepare context from tool results
        context = []
        for i, result in enumerate(tool_results):
            if result.success:
                context.append(f"Tool {i+1} Result: {json.dumps(result.data, indent=2)}")
            else:
                context.append(f"Tool {i+1} Error: {result.error}")
        
        context_str = "\n\n".join(context)
        
        system_prompt = f"""You are an AI assistant analyzing GitHub repository data.
        
        Processing strategy: {processing_strategy}
        
        Based on the tool results provided, generate a comprehensive and helpful response to the user's query.
        Format the response in a clear, structured way using markdown.
        
        Tool Results:
        {context_str}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Original query: {query}"}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"

def check_mcp_server():
    """Check if MCP server is running"""
    try:
        response = requests.get("http://localhost:3000/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_mcp_server():
    """Start the MCP server"""
    try:
        # This would typically start the Node.js MCP server
        # For demo purposes, we'll simulate this
        st.info("Starting MCP server...")
        time.sleep(2)
        return True
    except Exception as e:
        st.error(f"Failed to start MCP server: {str(e)}")
        return False

def main():
    st.set_page_config(
        page_title="GitHub Repository Analyzer",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("🔍 GitHub Repository Analyzer")
    st.subtitle("AI Agent powered by Model Context Protocol (MCP)")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API Keys
        openai_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        github_token = st.text_input("GitHub Token", type="password", value=os.getenv("GITHUB_TOKEN", ""))
        
        # Repository configuration
        repo_owner = st.text_input("Repository Owner", value="octocat")
        repo_name = st.text_input("Repository Name", value="Hello-World")
        
        # MCP Server status
        st.subheader("MCP Server Status")
        if check_mcp_server():
            st.success("🟢 MCP Server Running")
        else:
            st.error("🔴 MCP Server Not Running")
            if st.button("Start MCP Server"):
                if start_mcp_server():
                    st.rerun()
    
    # Main interface
    if not openai_key or not github_token:
        st.warning("Please provide OpenAI API Key and GitHub Token in the sidebar.")
        return
    
    # Initialize agent
    agent = GitHubAgent(openai_key, github_token)
    
    # Predefined queries
    st.header("🎯 Predefined Queries")
    
    predefined_queries = [
        "What are the latest issues in my repository?",
        "Show me the contents of the README.md file",
        "Find all Python files in the repository",
        "What are the recent commits on the main branch?",
        "Search for files containing 'add'",
        "Analyze the code and the issues in the repository and provide suggestions on how it can be fixed"
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        for i, query in enumerate(predefined_queries[:3]):
            if st.button(f"Query {i+1}", key=f"btn_{i}"):
                st.session_state.selected_query = query
    
    with col2:
        for i, query in enumerate(predefined_queries[3:], 3):
            if st.button(f"Query {i+1}", key=f"btn_{i}"):
                st.session_state.selected_query = query
    
    # Query input
    st.header("💬 Custom Query")
    
    if 'selected_query' in st.session_state:
        query = st.text_area("Enter your query:", value=st.session_state.selected_query, height=100)
        del st.session_state.selected_query
    else:
        query = st.text_area("Enter your query:", height=100)
    
    # Process query
    if st.button("🚀 Analyze Repository", type="primary"):
        if not query:
            st.warning("Please enter a query.")
            return
        
        with st.spinner("Analyzing query..."):
            # Step 1: Analyze query
            st.subheader("🧠 Query Analysis")
            analysis = agent.analyze_query(query)
            
            with st.expander("View Query Analysis"):
                st.json(analysis)
            
            # Step 2: Execute tools
            st.subheader("🔧 Tool Execution")
            if analysis.get("tools_to_use"):
                tool_results = agent.execute_tools(analysis["tools_to_use"])
                
                with st.expander("View Tool Results"):
                    for i, result in enumerate(tool_results):
                        st.write(f"**Tool {i+1} Result:**")
                        if result.success:
                            st.json(result.data)
                        else:
                            st.error(result.error)
            else:
                st.warning("No tools identified for execution.")
                tool_results = []
            
            # Step 3: Generate response
            st.subheader("📝 AI Response")
            response = agent.generate_response(
                query, 
                tool_results, 
                analysis.get("processing_strategy", "")
            )
            
            st.markdown(response)
    
    # Footer
    st.markdown("---")
    st.markdown("**GoML July 2025 Hackathon** | Built with Model Context Protocol (MCP)")

if __name__ == "__main__":
    main()