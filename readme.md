#  AI PR Review Agent

This project implements an intelligent PR (Pull Request) review agent using **LangGraph**, **LangChain**, and static analysis tools. It automates code analysis, standards enforcement, vulnerability checks, and enterprise rule validation using LLMs and tools like `pylint`, `bandit`, and `Checkmarx`.

---

##  Features

-  **Language Detection**: Detects Python, Java, or React code in PR diffs
-  **Static Analysis**:
  - `pylint`: Python code style and linting
  - `bandit`: Python vulnerability scanning
  - `Checkmarx`: Enterprise-grade SAST (optional)
-  **Enterprise Rule Checker** using LangChain and OpenAI
-  Ingests rules from PDF (`enterprise_rules.pdf`)
-  Built on LangGraph workflow engine
- REST API via FastAPI (`POST /review/pr/`)

---

## 📦 Installation

```bash
pip install \
  langgraph \
  langchain \
  langchain-community \
  openai \
  chromadb \
  fastapi \
  uvicorn \
  pypdf \
  python-dotenv \
  pylint \
  bandit

| Component       | Tool                     |
| --------------- | ------------------------ |
| Orchestrator    | LangGraph                |
| LLM API         | OpenAI (via LangChain)   |
| Rule Ingestion  | PyPDFLoader + Chroma     |
| Static Analysis | `pylint`, `bandit`, `cx` |
| API             | FastAPI + Uvicorn        |


--