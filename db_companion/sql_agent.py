from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
import os
from typing import Dict
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

app = FastAPI()

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load schema info from pg_dump file using robust path handling
BASE_DIR = Path(__file__).resolve().parent  # NEW
SCHEMA_FILE_PATH = BASE_DIR / "schema_dump.sql"  # NEW

def load_schema_from_file(path: Path) -> str:
    try:
        with open(path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return ""

SCHEMA_INFO = load_schema_from_file(SCHEMA_FILE_PATH)

# Database connection settings (use a secure vault or env vars in production)
DB_SETTINGS = {
    "host": "your-aurora-endpoint",
    "database": "your-db",
    "user": "your-username",
    "password": "your-password",
    "port": 5432
}

def get_db_connection():
    conn = psycopg2.connect(**DB_SETTINGS)
    conn.autocommit = True
    return conn

class QueryRequest(BaseModel):
    natural_language_query: str

@app.post("/query")
def query_db(request: QueryRequest):
    # Step 1: Generate SQL using OpenAI
    prompt = f"""
You are an expert SQL assistant.

Here is the database schema:
{SCHEMA_INFO}

Convert the following natural language question to a SQL query:
"{request.natural_language_query}"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        sql_query = response.choices[0].message.content.strip()
    except Exception as e:
        return {"error": f"Failed to generate SQL: {str(e)}"}

    # Step 2: Run SQL against Aurora PostgreSQL
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        return {"sql": sql_query, "error": f"DB execution error: {str(e)}"}

    return {"sql": sql_query, "results": results}
