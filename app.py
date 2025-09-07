# pip install chainlit python-dotenv langchain-google-genai deepmcpagent

import os
import asyncio
from dotenv import load_dotenv
import chainlit as cl
from langchain_google_genai import ChatGoogleGenerativeAI
from deepmcpagent import HTTPServerSpec, build_deep_agent
from datetime import datetime

load_dotenv()

# --- Config ---
ASSISTANT_AUTHOR = "MCP Assistant"  # Avatar in public/avatars/mcp-assistant.png

graph = None
loader = None
current_model = None


# ✅ Single selectable profile (removed Lite)
@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="gemini-2.5-flash",
            markdown_description="⚡ Using **Gemini 2.5 Flash** for fast and reliable reasoning with MCP websearch.",
            icon="https://raw.githubusercontent.com/cryxnet/DeepMCPAgent/refs/heads/main/docs/images/icon.png",
        ),
    ]


async def init_agent(selected_model: str):
    """Initialize MCP agent with websearch server + Gemini."""
    servers = {
        "websearch": HTTPServerSpec(
            url=f"https://mcp.linkup.so/sse?apiKey={os.getenv('LINKUP_API_KEY')}",
            transport="sse",
        ),
    }

    model = ChatGoogleGenerativeAI(
        model=selected_model,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    # Add current date/time to system instructions
    now = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")

    graph, loader = await build_deep_agent(
        servers=servers,
        model=model,
        instructions=(
            f"You are a powerful AI agent called MCP Assistant. "
            f"Today is {now}. "
            "Always provide accurate, up-to-date answers. "
            "Use the MCP websearch tools whenever external or live information is needed. "
            "Be precise, cite sources if available, and explain your reasoning clearly. "
            "If the user asks about current events, rely on websearch. "
            "Never guess—always prefer verified facts."
        ),
    )
    return graph, loader


@cl.on_chat_start
async def start():
    global graph, loader, current_model

    # ✅ Always use only the one profile
    selected_profile = cl.user_session.get("chat_profile")
    current_model = selected_profile or "gemini-2.5-flash"

    init_msg = cl.Message(content=f"🔄 Initializing MCP Agent with `{current_model}`...", author=ASSISTANT_AUTHOR)
    await init_msg.send()

    try:
        graph, loader = await init_agent(current_model)
        init_msg.content = f"✅ Agent Ready! Using `{current_model}`. Ask me anything..."
        await init_msg.update()
    except Exception as e:
        init_msg.content = f"❌ Initialization failed: {e}"
        await init_msg.update()


@cl.on_message
async def main(message: cl.Message):
    global graph
    user_query = message.content

    # Thinking placeholder
    thinking_msg = cl.Message(content="⏳ Thinking...", author=ASSISTANT_AUTHOR)
    await thinking_msg.send()

    if graph is None:
        thinking_msg.content = "Agent not initialized. Try restarting the app."
        await thinking_msg.update()
        return

    try:
        # Call MCP agent
        result = await graph.ainvoke({"messages": [{"role": "user", "content": user_query}]})

        # Collect AI responses
        final_answer = ""
        for msg in result.get("messages", []):
            if msg.__class__.__name__ == "AIMessage" and getattr(msg, "content", None):
                final_answer += msg.content

        thinking_msg.content = final_answer or "No answer returned."
        await thinking_msg.update()

    except Exception as e:
        thinking_msg.content = f"Error running agent: {e}"
        await thinking_msg.update()
