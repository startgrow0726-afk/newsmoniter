import os
import asyncpg
import asyncio

_pool = None

async def _dsn():
    return (
        f"postgresql://{os.getenv('POSTGRES_USER','newsmon')}:"
        f"{os.getenv('POSTGRES_PASSWORD','change_me_strong')}@"
        f"{os.getenv('POSTGRES_HOST','localhost')}:"
        f"{os.getenv('POSTGRES_PORT','5432')}/"
        f"{os.getenv('POSTGRES_DB','newsmon')}"
    )

async def connect_db():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=await _dsn(), min_size=1, max_size=10)
    return _pool

async def disconnect_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

import contextlib

@contextlib.asynccontextmanager
async def get_conn():
    conn = await _pool.acquire()
    try:
        yield conn
    finally:
        await _pool.release(conn)

async def execute(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)

async def fetch(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def init_db():
    await connect_db()
    async with _pool.acquire() as conn:
        # 스키마 적용
        with open(os.path.join(os.path.dirname(__file__), '..', '..', 'schema.sql'), 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        await conn.execute(schema_sql)
        print("Database schema applied successfully.")

        # 초기 데이터 삽입 (예시: 사용자 및 회사)
        # 사용자 데이터
        await conn.execute("INSERT INTO users (email, pw_hash) VALUES ($1, $2) ON CONFLICT (email) DO NOTHING", 'test@example.com', 'hashed_password')
        # 회사 데이터 (companies_context.json에서 마이그레이션)
        # 이 부분은 실제 companies_context.json 파일을 읽어서 처리해야 합니다.
        # 여기서는 예시로 NVIDIA, Tesla, Apple만 추가합니다.
        await conn.execute("INSERT INTO companies (name, tickers, aliases, context, negative, country) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (name) DO NOTHING",
                           'NVIDIA', ['NVDA'], ['nvidia', '엔비디아'], ['gpu', 'cuda'], [], 'US')
        await conn.execute("INSERT INTO companies (name, tickers, aliases, context, negative, country) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (name) DO NOTHING",
                           'Tesla', ['TSLA'], ['tesla', '테슬라'], ['model 3', 'elon musk'], [], 'US')
        await conn.execute("INSERT INTO companies (name, tickers, aliases, context, negative, country) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (name) DO NOTHING",
                           'Apple', ['AAPL'], ['apple'], ['iphone', 'ios'], [], 'US')
        
        # sources 테이블 초기 데이터 삽입 (server.py의 SOURCE_TRUST 룰 기반)
        # 실제 SOURCE_TRUST는 server.py에 정의되어 있으므로, 여기서는 임시로 몇 개만 추가합니다.
        await conn.execute("INSERT INTO sources (domain, trust) VALUES ($1, $2) ON CONFLICT (domain) DO NOTHING", 'reuters.com', 0.94)
        await conn.execute("INSERT INTO sources (domain, trust) VALUES ($1, $2) ON CONFLICT (domain) DO NOTHING", 'bloomberg.com', 0.94)
        await conn.execute("INSERT INTO sources (domain, trust) VALUES ($1, $2) ON CONFLICT (domain) DO NOTHING", 'techcrunch.com', 0.78)
        await conn.execute("INSERT INTO sources (domain, trust) VALUES ($1, $2) ON CONFLICT (domain) DO NOTHING", 'theverge.com', 0.75)
        await conn.execute("INSERT INTO sources (domain, trust) VALUES ($1, $2) ON CONFLICT (domain) DO NOTHING", 'engadget.com', 0.70)
        await conn.execute("INSERT INTO sources (domain, trust) VALUES ($1, $2) ON CONFLICT (domain) DO NOTHING", 'unknown', 0.60)
        
        print("Initial data inserted successfully.")