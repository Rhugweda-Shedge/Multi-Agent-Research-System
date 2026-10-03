# Multi-Agent Research System — Architecture & Design

## Overview

This is a multi-agent AI system that automates research on any topic. Given a topic, it searches the web, scrapes source content, writes a structured report, critiques that report, and — if the score is low — revises the report automatically. It can be run from the terminal or through a Streamlit web UI.

---

## High-Level Pipeline

```
User Input (topic)
       │
       ▼
┌─────────────────┐
│  Step 1: Search │  ← LangChain agent + Tavily API
│     Agent       │    Finds 5 web results (title, URL, snippet)
└────────┬────────┘
         │  search_results (titles, URLs, snippets)
         ▼
┌─────────────────┐
│  Step 2: Scrape │  ← Direct scrape_url tool calls
│   (Top 2 URLs)  │    Extracts top 2 URLs, scrapes both in sequence
└────────┬────────┘
         │  scraped_content (up to 3000 chars per URL, combined)
         ▼
┌─────────────────┐
│  Step 3: Writer │  ← LCEL chain (prompt | Claude Haiku | parser)
│     Chain       │    Combines search + scrape into a structured report
└────────┬────────┘
         │  report (markdown: Introduction, Key Findings, Conclusion, Sources)
         ▼
┌─────────────────┐
│  Step 4: Critic │  ← LCEL chain (prompt | Claude Sonnet | parser)
│     Chain       │    Scores across 5 dimensions, gives structured feedback
└────────┬────────┘
         │  feedback (Score X/10 with sub-scores, Strengths, Areas to Improve, Verdict)
         ▼
   Score < 7?
   ┌────┴────┐
  Yes        No
   │          │
   ▼          ▼
┌──────────┐  Final State Dict
│ Step 5:  │  { search_results, scraped_content,
│ Revision │    report, feedback, revised: False }
│  Chain   │  ← LCEL chain (prompt | Claude Haiku | parser)
└────┬─────┘    Writer revises report using critic's feedback
     │
     ▼
  Final State Dict
  { search_results, scraped_content,
    report (revised), feedback, revised: True }
```

---

## Project Structure

```
multi-agent-system/
├── agents.py          # LLM setup, agent builders, all chains
├── pipeline.py        # Orchestrates the pipeline (up to 5 steps)
├── tools.py           # LangChain tools: web_search and scrape_url
├── app.py             # Streamlit web UI
├── .env               # API keys and model config (never commit this)
├── .gitignore
├── requirements.txt
└── docs/
    └── architecture.md
```

---

## Components

### `agents.py` — LLM & Chain Factory

All AI components are defined here.

**`_get_llm()` — Fast LLM (Claude Haiku)**
- Used for search agent, scrape agent, writer chain, and revise chain
- Model from `ANTHROPIC_MODEL` env var (default: `claude-haiku-4-5-20251001`)
- API key from `ANTHROPIC_API_KEY` env var (explicitly passed, not implicit)
- `temperature=0` for deterministic, factual output
- Lazy-loaded on each call to avoid import-time credential failures

**`_get_critic_llm()` — Reasoning LLM (Claude Sonnet)**
- Used exclusively for the critic chain where nuanced analysis matters
- Model from `CRITIC_MODEL` env var (default: `claude-sonnet-5`)
- Same API key as above

**Search Agent (`build_search_agent`)**
- Built with `create_agent` from `langchain.agents`
- Has access to the `web_search` tool
- Invoked with a natural language prompt to find information on a topic

**Writer Chain**
- LCEL chain: `writer_prompt | _get_llm() | StrOutputParser()`
- Receives: `{topic}` + `{research}` (combined search results + scraped content)
- Outputs a structured markdown report: Introduction, Key Findings (min 3), Conclusion, Sources

**Critic Chain**
- LCEL chain: `critic_prompt | _get_critic_llm() | StrOutputParser()`
- Receives: `{topic}` + `{report}` — topic context is essential for judging relevance
- Scores across 5 explicit dimensions (2 points each):
  1. Relevance — does it directly answer the topic?
  2. Depth — are findings well-explained with detail?
  3. Sourcing — are credible URLs cited and used?
  4. Accuracy — are claims factual and grounded in the research?
  5. Clarity — is it well-structured and readable?
- Outputs: overall score, sub-scores, Strengths, Areas to Improve, one-line verdict

**Revise Chain**
- LCEL chain: `revise_prompt | _get_llm() | StrOutputParser()`
- Receives: `{topic}` + `{report}` + `{feedback}`
- Rewrites the report to address specific criticisms — not just rephrasing, but improving substance
- Only invoked when the critic score is below 7/10

---

### `tools.py` — LangChain Tools

Tools are Python functions decorated with `@tool` so agents can invoke them.

**`web_search(query: str) -> str`**
- Calls Tavily API with `max_results=5`
- Returns a formatted string: Title, URL, and a 300-character snippet per result
- Has full error handling — API failures return a descriptive error string instead of crashing

**`scrape_url(url: str) -> str`**
- Makes an HTTP GET request with a browser User-Agent header (avoids bot blocks)
- Checks HTTP status (`raise_for_status`) before parsing
- Parses HTML with BeautifulSoup, strips `<script>`, `<style>`, `<nav>`, `<footer>` tags
- Returns up to 3,000 characters of clean page text
- Has full error handling — network/HTTP failures return a descriptive error string

---

### `pipeline.py` — Orchestrator

`run_research_pipeline(topic: str) -> dict` runs all steps in sequence, passing data between them via a shared `state` dictionary.

| Key | Set by | Contains |
|-----|--------|----------|
| `state["search_results"]` | Step 1 | Formatted search result strings |
| `state["scraped_content"]` | Step 2 | Combined text scraped from top 2 URLs |
| `state["report"]` | Step 3 (or 5) | Full markdown research report (revised if Step 5 ran) |
| `state["feedback"]` | Step 4 | Structured critic review with sub-scores |
| `state["revised"]` | Step 5 | `True` if a revision was made, `False` otherwise |

The file can also be run directly from the terminal (`python pipeline.py`) for a CLI experience.

---

### `app.py` — Streamlit UI

Provides a browser-based interface to the pipeline.

- Text input for the research topic
- "Run Research" button (disabled when input is empty)
- `st.status` block shows live progress through the steps
- On completion, results are displayed in two columns:
  - **Left**: Research report (markdown rendered), download button (saves as `.md`), expandable raw search results and scraped content
  - **Right**: Critic feedback (markdown rendered)
- Errors are caught and displayed cleanly without crashing the UI

**To launch:**
```bash
streamlit run app.py
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| LLM (fast) | Claude Haiku (`claude-haiku-4-5-20251001`) — search, write, revise |
| LLM (reasoning) | Claude Sonnet (`claude-sonnet-5`) — critic only |
| Agent framework | LangChain (`langchain`, `langchain-core`) |
| Agent runtime | `langchain.agents.create_agent` |
| LLM chains | LangChain Expression Language (LCEL) |
| Web search | Tavily API (`tavily-python`) |
| Web scraping | `requests` + BeautifulSoup4 |
| UI | Streamlit |
| Config | `python-dotenv` |

---

## Environment Variables

All secrets and config live in a `.env` file (never committed to git).

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (from console.anthropic.com) |
| `TAVILY_API_KEY` | Yes | Tavily search API key (from app.tavily.com) |
| `ANTHROPIC_MODEL` | No | Model for writer/search/revise (default: `claude-haiku-4-5-20251001`) |
| `CRITIC_MODEL` | No | Model for critic chain (default: `claude-sonnet-5`) |

---

## Data Flow — Detailed

```
topic = "BRICS latest news"

Step 1 — Search Agent
  → Calls web_search("BRICS latest news")
  → Tavily returns 5 results
  → Agent returns formatted block with titles, URLs, snippets
  → state["search_results"] = "Title: ...\nURL: ...\nSnippet: ..."

Step 2 — Direct URL Scraping
  → Extracts top 2 URLs from state["search_results"] via regex
  → Calls scrape_url.invoke(url) for each
  → state["scraped_content"] = "[url1]\n...\n\n---\n\n[url2]\n..."

Step 3 — Writer Chain
  → Receives: topic + search_results + scraped_content
  → Claude Haiku writes a structured markdown report
  → state["report"] = "## Introduction\n..."

Step 4 — Critic Chain
  → Receives: topic + report
  → Claude Sonnet scores across 5 dimensions
  → state["feedback"] = "Score: 6/10\n- Relevance: 2/2\n- Depth: 1/2\n..."

Step 5 — Conditional Revision (only if score < 7)
  → Parses score from state["feedback"]
  → Calls revise_chain with topic + report + feedback
  → Claude Haiku rewrites the report addressing each criticism
  → state["report"] = revised version
  → state["revised"] = True
```

---

## Running the System

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Set up `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
CRITIC_MODEL=claude-sonnet-5
```

**CLI mode:**
```bash
python pipeline.py
```

**Web UI mode:**
```bash
streamlit run app.py
```
