# app.py
# 🔍 MCP WebSearch Chatbot

import os
import asyncio
import streamlit as st
import nest_asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from deepmcpagent import HTTPServerSpec, build_deep_agent

# Patch asyncio to allow nested loops (important for Streamlit)
nest_asyncio.apply()

# Load API keys
load_dotenv()

st.set_page_config(page_title="MCP WebSearch Chatbot", page_icon="🔍", layout="centered")
st.title("🔍 MCP WebSearch Chatbot")

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "graph" not in st.session_state:
    st.session_state.graph = None
if "loader" not in st.session_state:
    st.session_state.loader = None


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


# Initialize the agent once
if st.session_state.graph is None:
    with st.spinner("🔄 Initializing MCP Agent..."):
        loop = asyncio.get_event_loop()
        st.session_state.graph, st.session_state.loader = loop.run_until_complete(init_agent())


# Display previous chat messages
for role, content in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(content)


# Handle user input
if query := st.chat_input("Ask me anything..."):
    # Save user message
    st.session_state.chat_history.append(("user", query))
    with st.chat_message("user"):
        st.markdown(query)

    # Placeholder for assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("⏳ Thinking...")

        async def get_answer():
            """Run query against MCP agent."""
            result = await st.session_state.graph.ainvoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            final_answer = ""
            for msg in result["messages"]:
                if msg.__class__.__name__ == "AIMessage" and msg.content:
                    final_answer += msg.content
            return final_answer

        # Run async inside Streamlit safely
        loop = asyncio.get_event_loop()
        answer = loop.run_until_complete(get_answer())

        # Show assistant response
        message_placeholder.markdown(answer)

    # Save assistant message
    st.session_state.chat_history.append(("assistant", answer))
