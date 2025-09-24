from .pg import get_conn

def upsert_source(domain:str, trust:float|None=None)->int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO sources(domain, trust)
        VALUES (%s, COALESCE(%s, 0.7))
        ON CONFLICT (domain) DO UPDATE
          SET trust = COALESCE(EXCLUDED.trust, sources.trust)
        RETURNING id
        """, (domain, trust))
        return cur.fetchone()[0]

def upsert_feed(url:str, source_id:int|None=None, topic:str|None=None)->int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO feeds(url, source_id, topic)
        VALUES (%s, %s, %s)
        ON CONFLICT (url) DO UPDATE
          SET source_id=COALESCE(EXCLUDED.source_id, feeds.source_id),
              topic=COALESCE(EXCLUDED.topic, feeds.topic)
        RETURNING id
        """, (url, source_id, topic))
        return cur.fetchone()[0]

def list_active_feeds(limit:int=50)->list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        SELECT id, url, etag, last_modified, source_id
        FROM feeds WHERE active=true
        ORDER BY last_checked NULLS FIRST
        LIMIT %s
        """, (limit,))
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

def mark_feed_headers(feed_id:int, etag:str|None, last_modified:str|None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        UPDATE feeds SET etag=%s, last_modified=%s, last_checked=now() WHERE id=%s
        """, (etag, last_modified, feed_id))

def insert_article(row:dict)->int|None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
        INSERT INTO articles
          (url, canonical_url, url_hash, source_domain, source_id, title, body, lang, published_at)
        VALUES
          (%(url)s, %(canonical_url)s, %(url_hash)s, %(source_domain)s, %(source_id)s,
           %(title)s, %(body)s, %(lang)s, %(published_at)s)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """, row)
        r = cur.fetchone()
        return r[0] if r else None
