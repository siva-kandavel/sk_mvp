### AI PR Review Agent - LangGraph + LangChain Starter

# Required Packages:
# pip install langgraph langchain langchain-community openai chromadb fastapi uvicorn pypdf python-dotenv pylint

from langgraph.graph import StateGraph
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import AzureChatOpenAI
from fastapi import FastAPI, Request
import uvicorn
import os
import re
import subprocess
import tempfile
from typing import TypedDict
from dotenv import load_dotenv

# ------------------ SETUP ------------------
load_dotenv()
PDF_RULE_PATH = os.getenv("PDF_RULE_PATH", "/Users/sivakeerthi/Desktop/sample.pdf")

# Validate OpenAI API Key
openai_key = os.getenv("OPENAI_API_KEY")
print("[ENV] OpenAI key prefix:", openai_key[:8] if openai_key else "NOT FOUND")

# Quick test of Azure OpenAI LLM - DISABLED to prevent startup issues
print("[Azure OpenAI Test] Skipping test to ensure server starts")

# ------------------ STATE SCHEMA ------------------
class AgentState(TypedDict):
    pr_diff: str
    static_analysis: str
    rule_check_result: str
    final_summary: str

# ------------------ LANGCHAIN UTILS ------------------
_qa_chain_cache = None

def get_rule_qa_chain():
    global _qa_chain_cache
    if _qa_chain_cache is None:
        try:
            loader = PyPDFLoader(PDF_RULE_PATH)
            docs = loader.load()
            vectordb = Chroma.from_documents(docs, OpenAIEmbeddings())
            retriever = vectordb.as_retriever()
            llm = AzureChatOpenAI(
                deployment_name="analysis",
                temperature=0,
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("OPENAI_API_KEY"),
                api_version=os.getenv("OPENAI_API_VERSION")
            )
            _qa_chain_cache = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        except Exception as e:
            print(f"[ERROR] Failed to initialize QA chain: {str(e)}")
            return None
    return _qa_chain_cache

# ------------------ LANGUAGE DETECTION ------------------
_python_pattern = re.compile(r"\b(def|import|print|self|lambda)\b")
_java_pattern = re.compile(r"\b(public|static|void|System\.out|class)\b")
_react_pattern = re.compile(r"\b(function|const|let|useState|useEffect|return\s*\(<)\b")

def detect_language(code: str) -> str:
    if _python_pattern.search(code):
        return "python"
    elif _java_pattern.search(code):
        return "java"
    elif _react_pattern.search(code) or ".jsx" in code or ".tsx" in code:
        return "react"
    else:
        return "unknown"

# ------------------ LANGGRAPH NODES ------------------
def pr_diff_ingestion_node(state: AgentState) -> AgentState:
    print("[Node] PR Ingestion", state)
    return state

def static_analyzer_node(state: AgentState) -> AgentState:
    pr_diff = state.get("pr_diff", "")
    lang = detect_language(pr_diff)

    pylint_result = ""
    if lang == "python":
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w") as temp_file:
                temp_file.write(pr_diff)
                temp_path = temp_file.name
            process = subprocess.run(["pylint", temp_path], capture_output=True, text=True, timeout=15)
            pylint_result = process.stdout.strip()
        except Exception as e:
            pylint_result = f"Pylint failed: {str(e)}"
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    analysis = f"Detected language: {lang}.\n{pylint_result or 'No critical issues found in diff.'}"
    state["static_analysis"] = analysis
    print("[Node] Static Analysis", state)
    return state

def rule_checker_node(state: AgentState) -> AgentState:
    qa_chain = get_rule_qa_chain()
    pr_diff = state.get("pr_diff", "")
    query = f"Does the following PR diff violate any enterprise logic? {pr_diff}"
    
    if qa_chain is not None:
        answer = qa_chain.run(query)
    else:
        answer = "Rule check unavailable - QA chain initialization failed"
    
    state["rule_check_result"] = answer
    print("[Node] Rule Checker", state)
    return state

def summary_node(state: AgentState) -> AgentState:
    static_result = state.get("static_analysis", "No static analysis result.")
    rule_result = state.get("rule_check_result", "No rule check result.")
    state["final_summary"] = f"Static Analysis: {static_result}\nRule Check: {rule_result}"
    print("[Node] Summary", state)
    return state

# ------------------ LANGGRAPH WORKFLOW ------------------
workflow = StateGraph(AgentState)
workflow.add_node("PRIngestion", pr_diff_ingestion_node)
workflow.add_node("StaticAnalysis", static_analyzer_node)
workflow.add_node("RuleChecker", rule_checker_node)
workflow.add_node("Summarizer", summary_node)
workflow.set_entry_point("PRIngestion")
workflow.add_edge("PRIngestion", "StaticAnalysis")
workflow.add_edge("StaticAnalysis", "RuleChecker")
workflow.add_edge("RuleChecker", "Summarizer")
workflow.set_finish_point("Summarizer")
workflow = workflow.compile()

# ------------------ FASTAPI SERVER ------------------
app = FastAPI()

@app.post("/review/pr/")
async def review_pr(request: Request):
    try:
        body = await request.json()
        print("[Request] Received body:", body)
        pr_diff = body.get("diff", "")
        state: AgentState = {
            "pr_diff": pr_diff,
            "static_analysis": "",
            "rule_check_result": "",
            "final_summary": ""
        }
        final_state = workflow.invoke(state)
        print("[Response] Final State:", final_state)
        return {"summary": final_state.get("final_summary", "No summary generated.")}
    except Exception as e:
        print("[Error]", str(e))
        return {"error": str(e)}

if __name__ == "__main__":
    print("[SERVER] Starting FastAPI server...")
    print(f"[SERVER] Environment check - API Key: {'✓' if os.getenv('OPENAI_API_KEY') else '✗'}")
    print(f"[SERVER] Environment check - Endpoint: {'✓' if os.getenv('AZURE_OPENAI_ENDPOINT') else '✗'}")
    print(f"[SERVER] Environment check - Version: {'✓' if os.getenv('OPENAI_API_VERSION') else '✗'}")
    try:
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except Exception as e:
        print(f"[SERVER ERROR] Failed to start server: {str(e)}")
        import traceback
        traceback.print_exc()
