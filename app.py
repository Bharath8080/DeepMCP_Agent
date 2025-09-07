# pip install chainlit python-dotenv langchain-google-genai deepmcpagent

import os
import asyncio
from dotenv import load_dotenv
import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from deepmcpagent import HTTPServerSpec, build_deep_agent

load_dotenv()

# --- Config ---
ASSISTANT_AUTHOR = "MCP Assistant"  # -> place avatar in public/avatars/mcp-assistant.png

graph = None
loader = None

async def init_agent():
    """Initialize MCP agent with websearch server + Gemini."""
    servers = {
        "websearch": HTTPServerSpec(
            url=f"https://mcp.linkup.so/sse?apiKey={os.getenv('LINKUP_API_KEY')}",
            transport="sse",
        ),
    }

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    graph, loader = await build_deep_agent(
        servers=servers,
        model=model,
        instructions="You are a helpful AI agent. Use MCP websearch tools to answer with live info.",
    )
    return graph, loader

@cl.on_chat_start
async def start():
    global graph, loader
    # Send an initializing assistant message (will show avatar when public/avatars/<name>.png exists)
    init_msg = cl.Message(content="🔄 Initializing MCP Agent...", author=ASSISTANT_AUTHOR)
    await init_msg.send()

    try:
        graph, loader = await init_agent()
        # Update the same message to avoid duplicates
        init_msg.content = "✅ Agent Ready! Ask me anything..."
        await init_msg.update()
    except Exception as e:
        init_msg.content = f"❌ Initialization failed: {e}"
        await init_msg.update()

@cl.on_message
async def main(message: cl.Message):
    global graph
    user_query = message.content

    # Show a "thinking" assistant message which we'll update with the final answer
    thinking_msg = cl.Message(content="⏳ Thinking...", author=ASSISTANT_AUTHOR)
    await thinking_msg.send()

    if graph is None:
        thinking_msg.content = "Agent not initialized. Try restarting the app."
        await thinking_msg.update()
        return

    try:
        # Call the MCP agent (keep this same pattern you had)
        result = await graph.ainvoke({"messages": [{"role": "user", "content": user_query}]})

        # Extract content from AIMessage objects returned by your agent
        final_answer = ""
        for msg in result.get("messages", []):
            if msg.__class__.__name__ == "AIMessage" and getattr(msg, "content", None):
                final_answer += msg.content

        thinking_msg.content = final_answer or "No answer returned."
        await thinking_msg.update()

    except Exception as e:
        thinking_msg.content = f"Error running agent: {e}"
        await thinking_msg.update()
