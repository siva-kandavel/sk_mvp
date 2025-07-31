# Aurora Query Agent - Natural Language to SQL API

This FastAPI-based project lets you send **natural language queries** (e.g., "top 5 products sold last month") to an AI agent, which:

1. Converts the query into SQL using OpenAI GPT-4
2. Executes the SQL against an Aurora PostgreSQL database
3. Returns the result as JSON

---

## Features

* 🔌 FastAPI endpoint (`/query`)
* 🤖 AI-powered SQL generation using OpenAI GPT-4
* 🗃️ Schema loaded from `pg_dump`-generated SQL file
* 🔐 Secure API key loading via `.env`

---

## Requirements

* Python 3.8+
* Aurora PostgreSQL instance
* OpenAI API Key

---

## Installation

1. **Clone the repo** (or use the main Python file and schema file directly)

2. **Install dependencies**:

```bash
pip install fastapi uvicorn psycopg2-binary openai python-dotenv
```

3. **Create `.env` file** with your OpenAI API key:

```env
OPENAI_API_KEY=your-openai-key-here
```

4. **Generate schema dump from Aurora PostgreSQL**:

```bash
pg_dump -h <aurora-endpoint> -U <username> -d <dbname> --schema-only > schema_dump.sql
```

Place `schema_dump.sql` in the same directory as your Python file.

---

## Running the Server

```bash
uvicorn your_app_filename:app --reload
```

Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

---

## API Usage

### Endpoint:

`POST /query`

### Request JSON:

```json
{
  "natural_language_query": "Show top 5 products sold last month"
}
```

### Response JSON:

```json
{
  "sql": "SELECT name, SUM(quantity) ...",
  "results": [
    {"name": "Product A", "total": 120},
    {"name": "Product B", "total": 98}
  ]
}
```

---

## Notes

* This version assumes a static schema loaded from file. You can extend it to dynamically filter schema or cache results.
* For large schemas (\~90+ tables), consider pruning or summarizing the schema to stay within LLM token limits.

---

## License

MIT or your custom license here
