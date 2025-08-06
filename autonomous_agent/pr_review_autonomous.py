# Autonomous PR Review Agent API using LangChain's AgentExecutor

import os
from dotenv import load_dotenv
load_dotenv()

from langchain.agents import Tool
from langchain_openai import AzureChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
import subprocess
import tempfile
from fastapi import FastAPI, Request
import uvicorn

# ---------- TOOL DEFINITIONS ----------

PDF_RULE_PATH = os.getenv("PDF_RULE_PATH", "/Users/sivakeerthi/Desktop/UserStory.docx")

def _run_tool_on_temp_file(tool_name: str, code: str, file_suffix: str = ".py") -> str:
    """Helper function to run static analysis tools on temporary files."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix, mode="w") as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
        result = subprocess.run([tool_name, temp_path], capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except Exception as e:
        return f"{tool_name.capitalize()} failed: {str(e)}"
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass

def run_pylint(code: str) -> str:
    return _run_tool_on_temp_file("pylint", code)

def run_bandit(code: str) -> str:
    return _run_tool_on_temp_file("bandit", code)

_enterprise_qa_chain = None

def review_enterprise_rules(code: str) -> str:
    global _enterprise_qa_chain
    if _enterprise_qa_chain is None:
        try:
            loader = PyPDFLoader(PDF_RULE_PATH)
            docs = loader.load()
            vectordb = Chroma.from_documents(docs, OpenAIEmbeddings(), persist_directory="./rules_index")
            retriever = vectordb.as_retriever()
            llm = AzureChatOpenAI(deployment_name="analysis", temperature=0)
            _enterprise_qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
        except Exception as e:
            return f"Rule check initialization failed: {str(e)}"
    
    try:
        return _enterprise_qa_chain.run(f"Does this PR diff violate any enterprise rules? {code}")
    except Exception as e:
        return f"Rule check failed: {str(e)}"

# ---------- FASTAPI SERVER ----------

app = FastAPI()

@app.post("/review/pr/")
async def review_pr(request: Request):
    try:
        body = await request.json()
        pr_diff = body.get("diff", "")

        pylint_result = run_pylint(pr_diff)
        bandit_result = run_bandit(pr_diff)
        rule_result = review_enterprise_rules(pr_diff)

        return {
            "pylint": pylint_result,
            "bandit": bandit_result,
            "enterprise_rules": rule_result
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
