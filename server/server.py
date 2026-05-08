"""
mytracer 수집 서버 - FastAPI
트레이스 데이터를 받아 SQLite에 저장
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

DB_PATH = Path("traces.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id TEXT,
            name TEXT,
            timestamp TEXT,
            elapsed_ms REAL,
            status TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            tags TEXT,
            input TEXT,
            output TEXT,
            error TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✓ mytracer 서버 시작 | DB:", DB_PATH.absolute())
    yield


app = FastAPI(title="mytracer server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TraceIn(BaseModel):
    id: str
    name: str
    timestamp: str
    elapsed_ms: float
    status: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tags: List[str] = []
    input: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/traces")
async def receive_trace(trace: TraceIn):
    conn = get_db()
    conn.execute(
        """INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))""",
        (
            trace.id, trace.name, trace.timestamp, trace.elapsed_ms,
            trace.status, trace.input_tokens, trace.output_tokens,
            trace.total_tokens, json.dumps(trace.tags),
            trace.input, trace.output, trace.error
        )
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/traces")
async def list_traces(limit: int = 100, name: str = None, status: str = None):
    conn = get_db()
    query = "SELECT * FROM traces WHERE 1=1"
    params = []

    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d["tags"] or "[]")
        result.append(d)

    return result


@app.get("/api/stats")
async def get_stats():
    conn = get_db()
    stats = conn.execute("""
        SELECT
            COUNT(*) as total_traces,
            SUM(total_tokens) as total_tokens,
            AVG(elapsed_ms) as avg_elapsed_ms,
            SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as error_count,
            COUNT(DISTINCT name) as unique_functions
        FROM traces
    """).fetchone()

    by_name = conn.execute("""
        SELECT name,
               COUNT(*) as count,
               AVG(elapsed_ms) as avg_ms,
               SUM(total_tokens) as tokens,
               SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors
        FROM traces
        GROUP BY name
        ORDER BY count DESC
    """).fetchall()

    conn.close()

    return {
        "summary": dict(stats),
        "by_function": [dict(r) for r in by_name]
    }


@app.delete("/api/traces")
async def clear_traces():
    conn = get_db()
    conn.execute("DELETE FROM traces")
    conn.commit()
    conn.close()
    return {"ok": True, "message": "전체 삭제 완료"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8765, reload=True)
