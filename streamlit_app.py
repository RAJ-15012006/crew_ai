"""
CrewAI Research Pipeline — Streamlit UI
========================================
This app shows how 2 AI agents work together:
  Agent 1: Senior Research Analyst  → searches the web, gathers facts
  Agent 2: Content Writer           → turns those facts into a blog post

Run:  streamlit run streamlit_app.py
"""

# ── Fix: patch ChromaDB before ANY imports to prevent Pydantic type error
# on Streamlit Cloud (chroma_server_nofile is a Linux ulimit setting that
# chromadb tries to configure at import time — this sets a safe default).
import os
os.environ.setdefault("CHROMA_SERVER_NOFILE", "65536")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import streamlit as st
import time
import threading
import queue
from io import StringIO
import sys

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CrewAI Research Pipeline",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Global CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #0f1117;
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0a0c12;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] h2 {
    color: #60a5fa;
    letter-spacing: 1px;
}

/* Hide default streamlit chrome */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

/* ── Agent Cards ── */
.agent-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.agent-card.active {
    border-color: #3b82f6;
    box-shadow: 0 0 20px rgba(59,130,246,0.25);
}
.agent-card.done {
    border-color: #22c55e;
    box-shadow: 0 0 14px rgba(34,197,94,0.2);
}
.agent-card.waiting {
    opacity: 0.45;
}

.agent-title {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 0.3rem;
}
.agent-role-badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 999px;
    margin-bottom: 0.7rem;
}
.badge-analyst  { background:#1d4ed8; color:#bfdbfe; }
.badge-writer   { background:#7c3aed; color:#ede9fe; }

.agent-task {
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.5;
}

/* ── Arrow between agents ── */
.pipeline-arrow {
    text-align: center;
    font-size: 1.6rem;
    color: #334155;
    margin: 0.3rem 0;
    transition: color 0.5s;
}
.pipeline-arrow.lit { color: #3b82f6; }

/* ── Status badges ── */
.status-idle    { color: #64748b; }
.status-running { color: #f59e0b; }
.status-done    { color: #22c55e; }

/* ── Log box ── */
.log-box {
    background: #0d1117;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    color: #94a3b8;
    max-height: 240px;
    overflow-y: auto;
    line-height: 1.6;
}

/* ── Result box ── */
.result-box {
    background: #0d1117;
    border: 1px solid #22c55e44;
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
}

/* ── Title ── */
.app-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60a5fa, #818cf8, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.app-sub {
    color: #475569;
    font-size: 0.9rem;
    margin-top: -0.4rem;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────
for key, default in {
    "running": False,
    "agent1_status": "idle",   # idle | running | done
    "agent2_status": "idle",
    "agent1_log":    [],
    "agent2_log":    [],
    "final_output":  None,
    "error":         None,
    "topic":         "Medical Industry using Generative AI",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Sidebar: How It Works ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 CrewAI Pipeline")
    st.markdown("---")
    st.markdown("""
**What is CrewAI?**
CrewAI lets you build teams of AI agents that collaborate — each agent has a **role**, a **goal**, and **tools**.

---
**Your Pipeline:**

1. **🔍 Research Analyst**  
   Searches the web for real facts, news, and data on your topic.

2. **✍️ Content Writer**  
   Takes the research and writes a polished blog post in Markdown.

---
**How they connect:**  
Agent 1 finishes → hands its output → Agent 2 picks it up automatically. That's the "handoff" you saw in the terminal!
""")

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("<div class='app-title'>🤖 CrewAI Research Pipeline</div>", unsafe_allow_html=True)
st.markdown("<div class='app-sub'>Two AI agents working together — Researcher → Writer — live in your browser</div>", unsafe_allow_html=True)

# ─── Topic Input + Run Button ────────────────────────────────────────────────
col_input, col_btn = st.columns([4, 1])
with col_input:
    topic = st.text_input(
        "📌 Research Topic",
        value=st.session_state["topic"],
        placeholder="e.g. Electric Vehicles in India",
        disabled=st.session_state["running"],
        label_visibility="collapsed"
    )
with col_btn:
    run_clicked = st.button(
        "🚀 Run Crew",
        width="stretch",
        disabled=st.session_state["running"],
        type="primary"
    )

# ─── Layout: Pipeline Diagram | Logs | Output ───────────────────────────────
col_pipe, col_logs = st.columns([1, 2], gap="large")

# ── LEFT: Visual Pipeline ────────────────────────────────────────────────────
with col_pipe:
    st.markdown("### 🗂 Pipeline")

    # Agent 1 card
    a1_class = "active" if st.session_state["agent1_status"] == "running" else \
               "done"   if st.session_state["agent1_status"] == "done"    else "waiting"
    a1_icon  = "⚡" if a1_class == "active" else "✅" if a1_class == "done" else "🕐"

    st.markdown(f"""
    <div class='agent-card {a1_class}'>
        <div class='agent-title'>{a1_icon} Senior Research Analyst</div>
        <span class='agent-role-badge badge-analyst'>Agent 1</span>
        <div class='agent-task'>
            🔍 Searches the web using Serper<br>
            📊 Gathers facts, trends & citations<br>
            📝 Produces a structured research brief
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Arrow
    arrow_lit = "lit" if st.session_state["agent1_status"] == "done" else ""
    st.markdown(f"<div class='pipeline-arrow {arrow_lit}'>↓ hands off research ↓</div>", unsafe_allow_html=True)

    # Agent 2 card
    a2_class = "active" if st.session_state["agent2_status"] == "running" else \
               "done"   if st.session_state["agent2_status"] == "done"    else "waiting"
    a2_icon  = "⚡" if a2_class == "active" else "✅" if a2_class == "done" else "🕐"

    st.markdown(f"""
    <div class='agent-card {a2_class}'>
        <div class='agent-title'>{a2_icon} Content Writer</div>
        <span class='agent-role-badge badge-writer'>Agent 2</span>
        <div class='agent-task'>
            📥 Receives research from Agent 1<br>
            ✍️ Writes an engaging blog post<br>
            🔗 Adds citations & references section
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Status indicators
    st.markdown("---")
    s1 = st.session_state["agent1_status"]
    s2 = st.session_state["agent2_status"]
    icons = {"idle": "⬜", "running": "🟡", "done": "🟢"}
    st.markdown(f"{icons[s1]} **Agent 1** — `{s1.upper()}`")
    st.markdown(f"{icons[s2]} **Agent 2** — `{s2.upper()}`")

# ── RIGHT: Live Logs + Output ────────────────────────────────────────────────
with col_logs:
    tab_logs, tab_result = st.tabs(["📋 Live Agent Logs", "📄 Final Blog Post"])

    with tab_logs:
        log_placeholder_1 = st.empty()
        log_placeholder_2 = st.empty()

    with tab_result:
        result_placeholder = st.empty()

# ─── Helper: Capture stdout into a queue ────────────────────────────────────
class QueueWriter:
    """Redirects print/stdout output into a thread-safe queue."""
    def __init__(self, q, prefix=""):
        self.q = q
        self.prefix = prefix
        self.buf = ""

    def write(self, text):
        if text.strip():
            self.q.put((self.prefix, text.strip()))

    def flush(self):
        pass

# ─── Run Crew in Background Thread ──────────────────────────────────────────
def run_crew_thread(topic, q):
    """
    Runs the CrewAI pipeline in a background thread.
    Posts status messages + final result into queue q.
    """
    try:
        # ── Imports (inside thread to avoid Streamlit's import-time conflicts) ──
        import litellm
        from crewai import Agent, Task, Crew, LLM
        from crewai_tools import SerperDevTool
        from dotenv import load_dotenv
        load_dotenv()

        # Patch litellm to drop unsupported cache params
        litellm.drop_params = True
        _orig = litellm.completion
        def _patched(*args, **kwargs):
            for msg in kwargs.get("messages", []):
                msg.pop("cache_breakpoint", None)
                msg.pop("cache_control", None)
            return _orig(*args, **kwargs)
        litellm.completion = _patched

        # ── LLM & Tools ──────────────────────────────────────────────────────
        llm         = LLM(model="groq/llama-3.3-70b-versatile")
        search_tool = SerperDevTool(n=10)

        # ── Agent 1: Senior Research Analyst ─────────────────────────────────
        q.put(("STATUS", "agent1_running"))

        senior_research_analyst = Agent(
            role="Senior Research Analyst",
            goal=f"Research, analyze, and synthesize comprehensive information on {topic} from reliable web sources",
            backstory=(
                "You're an expert research analyst with advanced web research skills. "
                "You excel at finding, analyzing, and synthesizing information from "
                "across the internet using search tools. You're skilled at "
                "distinguishing reliable sources from unreliable ones, "
                "fact-checking, cross-referencing information, and "
                "identifying key patterns and insights. You provide "
                "well-organized research briefs with proper citations "
                "and source verification."
            ),
            tools=[search_tool],
            allow_delegation=False,
            verbose=True,
            llm=llm,
            use_system_prompt=True
        )

        # ── Agent 2: Content Writer ───────────────────────────────────────────
        content_writer = Agent(
            role="Content Writer",
            goal="Transform research findings into engaging, informative, and well-structured content pieces",
            backstory=(
                "You're a skilled content writer with expertise in translating complex research "
                "findings into compelling narratives. You ensure content is accurate, engaging, "
                "and tailored to the intended audience."
            ),
            tools=[search_tool],
            allow_delegation=False,
            verbose=True,
            llm=llm
        )

        # ── Task 1: Research ──────────────────────────────────────────────────
        research_task = Task(
            description=f"""
            1. Conduct comprehensive research on {topic} including:
               - Recent developments and news
               - Key industry trends and innovations
               - Expert opinions and analyses
               - Statistical data and market insights
            2. Evaluate source credibility and fact-check all information
            3. Organize findings into a structured research brief
            4. Include all relevant citations and sources
            """,
            expected_output="""
            A detailed research report containing:
            - Executive summary of key findings
            - Comprehensive analysis of current trends
            - List of verified facts and statistics
            - All citations and links to original sources
            """,
            agent=senior_research_analyst
        )

        # ── Task 2: Writing ───────────────────────────────────────────────────
        writing_task = Task(
            description="""
            Using the research brief provided, create an engaging blog post that:
            1. Transforms technical information into accessible content
            2. Maintains all factual accuracy and citations
            3. Includes an attention-grabbing intro, clear headings, and a conclusion
            4. Preserves all source citations in [Source: URL] format
            5. Includes a References section at the end
            """,
            expected_output="""
            A polished blog post in Markdown format with:
            - Title, Introduction, Main sections, Conclusion, References
            """,
            agent=content_writer
        )

        # ── Crew: Sequential pipeline ─────────────────────────────────────────
        crew = Crew(
            agents=[senior_research_analyst, content_writer],
            tasks=[research_task, writing_task],
            verbose=True,
            planning=False,
            memory=False  # Disabled to avoid ChromaDB errors on Streamlit Cloud
        )

        # Redirect verbose stdout into the queue so we can show live logs
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(q, prefix="LOG")

        result = crew.kickoff(inputs={"topic": topic})

        sys.stdout = old_stdout

        # Signal agent transitions (heuristic — after kickoff completes)
        q.put(("STATUS", "agent1_done"))
        q.put(("STATUS", "agent2_done"))
        q.put(("RESULT", str(result)))

    except Exception as e:
        q.put(("ERROR", str(e)))


# ─── Trigger on Button Click ─────────────────────────────────────────────────
if run_clicked:
    # Reset all state
    st.session_state.update({
        "running":       True,
        "agent1_status": "idle",
        "agent2_status": "idle",
        "agent1_log":    [],
        "agent2_log":    [],
        "final_output":  None,
        "error":         None,
        "topic":         topic,
    })
    st.session_state["_queue"] = queue.Queue()

    # Launch background thread
    t = threading.Thread(
        target=run_crew_thread,
        args=(topic, st.session_state["_queue"]),
        daemon=True
    )
    t.start()
    st.session_state["_thread"] = t
    st.rerun()


# ─── Poll Queue While Running ────────────────────────────────────────────────
if st.session_state["running"]:
    q = st.session_state.get("_queue")

    if q:
        # Drain all messages currently in queue
        while not q.empty():
            msg_type, payload = q.get_nowait()

            if msg_type == "STATUS":
                if payload == "agent1_running":
                    st.session_state["agent1_status"] = "running"
                elif payload == "agent1_done":
                    st.session_state["agent1_status"] = "done"
                    st.session_state["agent2_status"] = "running"
                elif payload == "agent2_done":
                    st.session_state["agent2_status"] = "done"

            elif msg_type == "LOG":
                current_agent = st.session_state.get("agent2_status")
                if current_agent in ("running", "done") and st.session_state["agent1_status"] == "done":
                    st.session_state["agent2_log"].append(payload)
                else:
                    st.session_state["agent1_log"].append(payload)

            elif msg_type == "RESULT":
                st.session_state["final_output"] = payload
                st.session_state["running"] = False

            elif msg_type == "ERROR":
                st.session_state["error"] = payload
                st.session_state["running"] = False

    # Show spinner while running
    if st.session_state["running"]:
        with col_logs:
            with tab_logs:
                st.info("⏳ Agents are working… this takes 1–3 minutes. Logs appear below as they come in.")

        # Auto-refresh every 3 seconds while running
        time.sleep(3)
        st.rerun()

# ─── Render Logs ─────────────────────────────────────────────────────────────
with col_logs:
    with tab_logs:
        if st.session_state["agent1_log"]:
            st.markdown("**🔍 Agent 1 — Research Analyst**")
            log1_text = "\n".join(st.session_state["agent1_log"][-40:])  # last 40 lines
            st.code(log1_text, language=None)

        if st.session_state["agent2_log"]:
            st.markdown("**✍️ Agent 2 — Content Writer**")
            log2_text = "\n".join(st.session_state["agent2_log"][-40:])
            st.code(log2_text, language=None)

        if st.session_state["error"]:
            st.error(f"❌ Error: {st.session_state['error']}")

    with tab_result:
        if st.session_state["final_output"]:
            st.success("✅ Blog post generated! Copy it below.")
            st.markdown(st.session_state["final_output"])

            # Download button
            st.download_button(
                "⬇️ Download as .md",
                data=st.session_state["final_output"],
                file_name=f"{topic[:30].replace(' ','_')}_blog.md",
                mime="text/markdown"
            )
        elif not st.session_state["running"]:
            st.info("👈 Enter a topic and click **Run Crew** to generate a blog post.")
