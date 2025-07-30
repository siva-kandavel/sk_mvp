# Autonomous PR Review Agent API using LangChain's AgentExecutor

import os
from dotenv import load_dotenv
load_dotenv()

from langchain.agents import Tool
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
import subprocess
import tempfile
from fastapi import FastAPI, Request
import uvicorn

# ---------- TOOL DEFINITIONS ----------

PDF_RULE_PATH = "/Users/sivakeerthi/Desktop/UserStory.docx"

def run_pylint(code: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w") as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
        result = subprocess.run(["pylint", temp_path], capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except Exception as e:
        return f"Pylint failed: {str(e)}"

def run_bandit(code: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".py", mode="w") as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name
        result = subprocess.run(["bandit", temp_path], capture_output=True, text=True, timeout=15)
        return result.stdout.strip()
    except Exception as e:
        return f"Bandit failed: {str(e)}"

def review_enterprise_rules(code: str) -> str:
    try:
        loader = PyPDFLoader(PDF_RULE_PATH)
        docs = loader.load()
        vectordb = Chroma.from_documents(docs, OpenAIEmbeddings(), persist_directory="./rules_index")
        retriever = vectordb.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(llm=ChatOpenAI(), retriever=retriever)
        return qa_chain.run(f"Does this PR diff violate any enterprise rules? {code}")
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