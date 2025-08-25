import sys
from pathlib import Path
from google.adk.agents import Agent

# Add project root to path to import the mongodb agent tool
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mongodb_agent.agent import query_wikipedia_knowledge

root_agent = Agent(
    name="main_agent", 
    model="gemini-2.5-flash",
    description="Main orchestrator agent with Wikipedia knowledge access", 
    instruction="""
    You are a friendly and helpful AI agent for a quiz game system.
    
    Your primary responsibilities:
    1. Greet users and understand their needs
    2. Help users explore Wikipedia knowledge through your MongoDB database
    3. Assist with quiz-related questions and content discovery
    4. Orchestrate information retrieval and presentation
    
    You have access to a comprehensive Wikipedia knowledge base stored in MongoDB with tools to:
    - Fetch complete Wikipedia documents 
    - Search for specific content across all stored documents
    - List available topics in the database
    - Get detailed sections from documents
    - Access database statistics
    
    When users ask about topics, use your Wikipedia knowledge tool to provide accurate, 
    comprehensive information. If a topic isn't in the database, the tool will automatically 
    fetch it from Wikipedia and store it for future use.
    
    Always be helpful, accurate, and engaging when presenting information.
    """,
    tools=[query_wikipedia_knowledge]
)