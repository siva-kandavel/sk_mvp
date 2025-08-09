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
from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from typing import Optional, Dict, List, Any
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

# ---------- FILE PARSING FUNCTIONS ----------

def parse_pr_diff(diff_content: str) -> Dict[str, Dict]:
    """Parse multi-file diff into structured format"""
    files = {}
    current_file = None
    current_changes = []
    
    for line in diff_content.split('\n'):
        if line.startswith('--- a/') or line.startswith('+++ b/'):
            if current_file and current_changes:
                if current_file not in files:
                    files[current_file] = {'changes': []}
                files[current_file]['changes'].extend(current_changes)
            
            if line.startswith('--- a/'):
                current_file = line.replace('--- a/', '').strip()
            elif line.startswith('+++ b/'):
                current_file = line.replace('+++ b/', '').strip()
            current_changes = []
            
        elif line.startswith('@@'):
            if current_file:
                if current_file not in files:
                    files[current_file] = {'changes': [], 'line_info': []}
                files[current_file]['line_info'] = files[current_file].get('line_info', [])
                files[current_file]['line_info'].append(line)
        elif line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
            current_changes.append(line)
    
    if current_file and current_changes:
        if current_file not in files:
            files[current_file] = {'changes': []}
        files[current_file]['changes'].extend(current_changes)
    
    return files

def parse_codebase(codebase_content: str) -> Dict[str, str]:
    """Parse codebase file into file_path: content mapping"""
    files = {}
    current_file = None
    current_content = []
    
    for line in codebase_content.split('\n'):
        if line.startswith('=== FILE:') and line.endswith('==='):
            if current_file:
                files[current_file] = '\n'.join(current_content)
            
            current_file = line.replace('=== FILE:', '').replace('===', '').strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_file:
        files[current_file] = '\n'.join(current_content)
    
    return files

def find_dependencies(file_content: str) -> List[str]:
    """Extract import statements and dependencies from file content"""
    dependencies = []
    for line in file_content.split('\n'):
        line = line.strip()
        if line.startswith(('import ', 'from ')):
            dependencies.append(line)
    return dependencies

def analyze_change_impact(changes: List[str], full_file_content: str) -> Dict[str, Any]:
    """Analyze the impact of changes within the context of the full file"""
    added_lines = [line[1:] for line in changes if line.startswith('+')]
    removed_lines = [line[1:] for line in changes if line.startswith('-')]
    
    return {
        "lines_added": len(added_lines),
        "lines_removed": len(removed_lines),
        "net_change": len(added_lines) - len(removed_lines),
        "complexity_impact": "Low" if len(added_lines) + len(removed_lines) < 10 else "High"
    }

def find_cross_references(filename: str, codebase_files: Dict[str, str]) -> List[str]:
    """Find files that reference the changed file"""
    references = []
    base_name = filename.replace('.py', '').replace('/', '.')
    
    for file_path, content in codebase_files.items():
        if file_path != filename and base_name in content:
            references.append(file_path)
    
    return references

# ---------- FASTAPI SERVER ----------

app = FastAPI()

MAX_DIFF_SIZE = 10 * 1024 * 1024  # 10MB
MAX_CODEBASE_SIZE = 100 * 1024 * 1024  # 100MB

@app.post("/review/pr/")
async def review_pr(request: Request):
    """Original JSON endpoint for backward compatibility"""
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

@app.post("/review/pr/files/")
async def review_pr_files(
    pr_diff_file: UploadFile = File(..., description="PR diff file (.txt, .patch, .diff)"),
    codebase_file: Optional[UploadFile] = File(None, description="Codebase file (.txt)"),
    analysis_scope: str = Form("full", description="Analysis scope: diff_only, contextual, full")
):
    """Enhanced endpoint that accepts file uploads for PR diff and codebase"""
    try:
        if pr_diff_file.size and pr_diff_file.size > MAX_DIFF_SIZE:
            raise HTTPException(status_code=400, detail="PR diff file too large (max 10MB)")
        
        if codebase_file and codebase_file.size and codebase_file.size > MAX_CODEBASE_SIZE:
            raise HTTPException(status_code=400, detail="Codebase file too large (max 100MB)")
        
        pr_diff_content = await pr_diff_file.read()
        pr_diff_text = pr_diff_content.decode('utf-8')
        
        codebase_text = None
        if codebase_file:
            codebase_content = await codebase_file.read()
            codebase_text = codebase_content.decode('utf-8')
        
        return await analyze_with_context(pr_diff_text, codebase_text, analysis_scope)
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Files must be UTF-8 encoded text files")
    except Exception as e:
        return {"error": str(e)}

async def analyze_with_context(pr_diff: str, codebase: Optional[str] = None, scope: str = "full"):
    """Enhanced analysis function that handles both diff and codebase context"""
    
    diff_files = parse_pr_diff(pr_diff)
    codebase_files = parse_codebase(codebase) if codebase else {}
    
    results = {}
    
    for filename, changes in diff_files.items():
        file_analysis = {
            'static_analysis': {
                'pylint': run_pylint('\n'.join(changes.get('changes', []))),
                'bandit': run_bandit('\n'.join(changes.get('changes', [])))
            },
            'enterprise_rules': review_enterprise_rules('\n'.join(changes.get('changes', []))),
            'change_summary': {
                'lines_changed': len(changes.get('changes', [])),
                'line_info': changes.get('line_info', [])
            }
        }
        
        if scope in ["contextual", "full"] and filename in codebase_files:
            full_file_content = codebase_files[filename]
            file_analysis['context_analysis'] = {
                'dependencies': find_dependencies(full_file_content),
                'impact_analysis': analyze_change_impact(changes.get('changes', []), full_file_content),
                'cross_file_refs': find_cross_references(filename, codebase_files)
            }
        
        results[filename] = file_analysis
    
    total_files = len(diff_files)
    total_changes = sum(len(changes.get('changes', [])) for changes in diff_files.values())
    
    summary = {
        'total_files_changed': total_files,
        'total_lines_changed': total_changes,
        'analysis_scope': scope,
        'has_codebase_context': codebase is not None
    }
    
    recommendations = []
    if total_changes > 100:
        recommendations.append("Large PR detected - consider breaking into smaller changes")
    if any('error' in str(analysis).lower() for analysis in results.values()):
        recommendations.append("Some analysis tools encountered errors - review manually")
    if codebase and any(analysis.get('context_analysis', {}).get('cross_file_refs') for analysis in results.values()):
        recommendations.append("Changes affect multiple files - ensure integration testing")
    
    return {
        'file_analyses': results,
        'summary': summary,
        'recommendations': recommendations,
        'analysis_timestamp': str(os.popen('date').read().strip())
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
