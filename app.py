# pip install streamlit python-dotenv langchain-google-genai deepmcpagent 

import os
import asyncio
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from deepmcpagent import HTTPServerSpec, build_deep_agent

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
if "query" not in st.session_state:
    st.session_state.query = ""

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
        st.session_state.graph, st.session_state.loader = asyncio.run(init_agent())

# Input box with submit button
query = st.text_input("Ask me anything...", key="query")
submit = st.button("Submit")

if submit and query:
    # Clear history for fresh question
    st.session_state.chat_history = []

    # Show user message
    st.session_state.chat_history.append(("user", query))
    st.markdown(f"**You asked:** {query}")

    # Placeholder for assistant response
    with st.spinner("⏳ Thinking..."):

        async def get_answer():
            result = await st.session_state.graph.ainvoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            final_answer = ""
            for msg in result["messages"]:
                if msg.__class__.__name__ == "AIMessage" and msg.content:
                    final_answer += msg.content
            return final_answer

        answer = asyncio.run(get_answer())
        st.markdown(f"**Answer:** {answer}")

    # Save assistant message
    st.session_state.chat_history.append(("assistant", answer))
