from google.adk.agents import Agent

root_agent = Agent(
    name="main_agent", 
    model ="gemini-2.5-flash",
    description ="Greeting agent and orchestrator of the agents team", 
    instruction="""
    You are a friendly and helpful AI agent. 
    Your task is to greet the user and understand their needs.
    """
)