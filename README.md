# 🤖 CrewAI Multi-Agent Research Pipeline

> **This is NOT a simple AI chatbot.**  
> This is a **multi-agent AI system** — a team of specialized AI agents that work together, where each agent has a dedicated job and hands its output to the next agent automatically.

---

## 🧠 What is CrewAI?

Most people think of AI as a single model you talk to — like ChatGPT.

**CrewAI is different.** It lets you build a *crew* of AI agents, each with:
- A specific **role** (e.g., Researcher, Writer)
- A specific **goal** (what it's trying to achieve)
- Specific **tools** it can use (e.g., web search)
- A specific **task** assigned to it

These agents work **sequentially** — Agent 1 completes its task and passes the result to Agent 2, who then does *its* task using that result. It's like a real workplace pipeline, except fully automated with AI.

---

## 🔄 How This Project Works — The Pipeline

```
You give a topic
        │
        ▼
┌─────────────────────────────────────────────┐
│  🔍 Agent 1: Senior Research Analyst        │
│                                             │
│  • Searches the web using Serper API        │
│  • Finds recent news, trends, statistics    │
│  • Verifies facts and sources               │
│  • Produces a structured research brief     │
└───────────────────┬─────────────────────────┘
                    │
                    │  ← hands off research output
                    │
                    ▼
┌─────────────────────────────────────────────┐
│  ✍️  Agent 2: Content Writer                │
│                                             │
│  • Receives the research brief from Agent 1 │
│  • Transforms it into an engaging blog post │
│  • Adds proper headings, intro, conclusion  │
│  • Preserves all citations and references   │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
           📄 Final Blog Post (Markdown)
```

**The key insight:** Agent 2 never searches the web itself. It only receives what Agent 1 found and then writes. Each agent does *one thing* and does it well. That's the power of CrewAI.

---

## 📁 Project Files

| File | Purpose |
|---|---|
| `app.py` | Core CrewAI pipeline — defines agents, tasks, and runs the crew |
| `streamlit_app.py` | Web UI — run this to see the pipeline live in your browser |
| `.env` | API keys (Groq LLM + Serper search) — **never commit this to GitHub** |
| `requirements.txt` | Python dependencies |
| `README.md` | This file |

---

## ⚙️ Tech Stack

| Component | Technology | Why |
|---|---|---|
| **Agent Framework** | [CrewAI](https://crewai.com) | Orchestrates multi-agent pipelines |
| **LLM (Brain)** | Groq `llama-3.3-70b-versatile` | Fast, free-tier LLM via Groq API |
| **Web Search Tool** | Serper API | Gives Agent 1 real-time Google search |
| **Web UI** | Streamlit | Visual dashboard to run and watch the pipeline |
| **LLM Routing** | LiteLLM | Handles LLM API calls cleanly |

---

## 🚀 Setup & Run

### 1. Clone the repository

```bash
git clone https://github.com/RAJ-15012006/crew_ai.git
cd crew_ai
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# OR
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install crewai crewai-tools python-dotenv streamlit plotly litellm
```

### 4. Set up your API keys

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
SERPER_API_KEY=your_serper_api_key_here
LITELLM_DROP_PARAMS=True
```

- **Groq API Key** → Free at [console.groq.com](https://console.groq.com)
- **Serper API Key** → Free tier at [serper.dev](https://serper.dev)

### 5. Run the pipeline

**Option A — Terminal (raw output):**
```bash
python app.py
```

**Option B — Streamlit UI (visual, recommended):**
```bash
streamlit run streamlit_app.py
```
Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🖥️ Streamlit UI — What You'll See

When you run `streamlit_app.py`, you get a visual dashboard:

- **Left panel** — Agent cards light up 🟡 when active, turn 🟢 when done
- **Arrow between agents** — Glows blue when the handoff happens
- **Live Logs tab** — See each agent's internal thinking in real time
- **Final Blog Post tab** — The finished Markdown blog post, downloadable as `.md`

---

## 💡 Understanding the Agent Handoff

This is the most important concept. Here's the exact flow in code:

```python
# Agent 1 is assigned research_task
research_task = Task(
    description="Research the topic thoroughly...",
    agent=senior_research_analyst   # ← Agent 1 does this
)

# Agent 2 is assigned writing_task
writing_task = Task(
    description="Using the research brief provided...",
    agent=content_writer            # ← Agent 2 does this
)

# The Crew runs them IN SEQUENCE
crew = Crew(
    agents=[senior_research_analyst, content_writer],
    tasks=[research_task, writing_task],   # ← Order matters!
)

result = crew.kickoff(inputs={"topic": "Medical AI"})
# Agent 1 runs → finishes → Agent 2 picks up its output → finishes → done
```

CrewAI automatically passes Agent 1's output as **context** to Agent 2. You don't have to write any code to do the handoff — the framework handles it.

---

## 🔑 Key Concepts

| Concept | What It Means |
|---|---|
| **Agent** | An AI worker with a role, goal, backstory, and tools |
| **Task** | A specific job assigned to an agent, with a description and expected output |
| **Crew** | The team — a group of agents + tasks, run in sequence |
| **Tool** | Something an agent can *do* (e.g., search the web, read a file) |
| **Handoff** | When Agent 1's output automatically becomes Agent 2's input |
| **Sequential Process** | Agents run one after another (default in this project) |

---

## 📊 Sample Output

After running the pipeline on topic **"Medical Industry using Generative AI"**:

**Agent 1 produces:** A structured research brief with bullet points, stats, and source URLs.

**Agent 2 produces:** A full blog post like:

```markdown
# How Generative AI is Transforming the Medical Industry

## Introduction
The healthcare sector is witnessing...

## Key Trends
1. AI-assisted diagnostics...
2. Drug discovery acceleration...

## References
- [Source: https://...]
```

---

## 🛡️ Security Note

Your `.env` file contains private API keys. Make sure it is listed in `.gitignore`:

```
.env
.venv/
__pycache__/
*.pyc
```

**Never commit API keys to a public repository.**

---

## 🙋 Author

**Raj Samrendra Kumar**  
GitHub: [@RAJ-15012006](https://github.com/RAJ-15012006)

---

## 📜 License

MIT License — free to use, modify, and share.
