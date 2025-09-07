# pip install streamlit python-dotenv langchain-google-genai deepmcpagent

import os
import asyncio
import datetime
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from deepmcpagent import HTTPServerSpec, build_deep_agent

# Load API keys
load_dotenv()

st.set_page_config(page_title="MCP WebSearch Chatbot", page_icon="🔍", layout="centered")
st.title("🔍 MCP WebSearch Chatbot")

# Quick env checks
if not os.getenv("GOOGLE_API_KEY"):
    st.warning("Missing GOOGLE_API_KEY in environment.")
if not os.getenv("LINKUP_API_KEY"):
    st.warning("Missing LINKUP_API_KEY in environment (needed for MCP websearch).")

# Session state
if "graph" not in st.session_state:
    st.session_state.graph = None
if "loader" not in st.session_state:
    st.session_state.loader = None

async def init_agent():
    """Initialize MCP agent with websearch server + Gemini, with 'search-first' behavior."""
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

    today = datetime.date.today().strftime("%B %d, %Y")
    instructions = f"""
You are a helpful AI agent. Today is {today}.
CRITICAL:
- For any time-sensitive, newsy, or factual queries that may have changed since 2024
  (e.g., sports results like “who won…”, schedules, prices, weather, finance),
  you MUST call the `websearch` MCP tool FIRST and base your answer ONLY on those results.
- Do NOT rely on prior knowledge for such queries.
- Provide concise answers. At the end, list 2–4 sources as bullet points with titles and URLs.
"""

    graph, loader = await build_deep_agent(
        servers=servers,
        model=model,
        instructions=instructions,
    )
    return graph, loader

# Initialize once
if st.session_state.graph is None:
    with st.spinner("🔄 Initializing MCP Agent..."):
        st.session_state.graph, st.session_state.loader = asyncio.run(init_agent())

# Input + Submit
user_input = st.text_input("Ask me anything...", key="user_input")
submit = st.button("Submit")

def extract_ai_text(result) -> str:
    final = []
    for msg in result.get("messages", []):
        name = msg.__class__.__name__
        content = getattr(msg, "content", None)
        if name == "AIMessage" and content:
            final.append(str(content))
    return "\n".join(final).strip()

if submit and user_input:
    query = user_input.strip()
    with st.spinner("⏳ Thinking..."):
        answer_text = ""
        try:
            # Prefer sync call to avoid nested event loop issues
            result = st.session_state.graph.invoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            answer_text = extract_ai_text(result)
        except Exception:
            # Fallback to async if needed
            async def get_answer():
                result_async = await st.session_state.graph.ainvoke(
                    {"messages": [{"role": "user", "content": query}]}
                )
                return extract_ai_text(result_async)
            answer_text = asyncio.run(get_answer())

    # Plain text output only (no "You asked", no chat bubbles)
    if answer_text:
        st.markdown(answer_text)
    else:
        st.info("No answer produced. Ensure LINKUP_API_KEY is valid so the websearch tool can run.")

    # Clear input safely
    st.session_state.pop("user_input", None)
