import os
from dotenv import load_dotenv
from api.storage.pg import get_conn

def seed():
    load_dotenv(dotenv_path='api/.env')
    if os.getenv("SEED_TEST_DATA") != "true":
        print("SEED_TEST_DATA is not true, skipping seeding.")
        return

    print("Seeding database with test data...")
    
    sql = """
    -- 회사
    INSERT INTO companies(name, tickers, aliases, context)
    VALUES ('NVIDIA', '{NVDA}', '{"NVIDIA","엔비디아","Nvidia"}', '{"GPU","CUDA","H100","H200","GB200","NVLink"}')
    ON CONFLICT (lower(name)) DO NOTHING;

    -- 기사 1: 규제(HIGH)
    WITH ins AS (
      INSERT INTO articles(url, canonical_url, url_hash, source_domain, title, body, lang, published_at)
      VALUES ('https://www.reuters.com/nvidia-probe',
              'https://www.reuters.com/nvidia-probe',
              '1234567891', 'reuters.com',
              'EU opens antitrust probe into NVIDIA over data access',
              'The European Commission opened an antitrust probe into NVIDIA...',
              'en', now() - interval '2 hours')
      ON CONFLICT (url_hash) DO UPDATE SET title = EXCLUDED.title RETURNING id
    ), meta_ins AS (
      INSERT INTO article_meta(article_id, category, topic_tags, related_event, sentiment, positivity_pct, accuracy_pct, importance_pct, impact_level, severity)
      SELECT id, 'regulation', '{"반도체","GPU","AI"}', 'antitrust probe', -0.4, 30, 93, 88, '큼', 'HIGH' FROM ins
      ON CONFLICT (article_id) DO NOTHING
    )
    INSERT INTO article_entities(article_id, company_id, confidence, matched)
    SELECT ins.id, (SELECT id FROM companies WHERE lower(name)='nvidia'), 0.92, 'NVDA'
    FROM ins
    ON CONFLICT (article_id, company_id) DO NOTHING;

    -- 기사 2: 에코(간접)
    WITH ins AS (
      INSERT INTO articles(url, canonical_url, url_hash, source_domain, title, body, lang, published_at)
      VALUES ('https://www.ft.com/hbm-ramp',
              'https://www.ft.com/hbm-ramp',
              '1234567892', 'ft.com',
              'SK hynix ramps HBM3E output to support AI GPUs demand',
              'HBM3E capacity expansion may ease constraints for NVIDIA supply...',
              'en', now() - interval '5 hours')
      ON CONFLICT (url_hash) DO UPDATE SET title = EXCLUDED.title RETURNING id
    )
    INSERT INTO article_meta(article_id, category, topic_tags, related_event, sentiment, positivity_pct, accuracy_pct, importance_pct, impact_level, severity)
    SELECT id, 'supply_chain', '{"반도체","HBM","메모리"}', NULL, 0.1, 55, 90, 62, '보통', 'MEDIUM' FROM ins
    ON CONFLICT (article_id) DO NOTHING;
    """
    
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")

if __name__ == "__main__":
    # This script needs to be run in an environment where DB credentials are available.
    # You can run it with: python -m seed_db
    # Make sure to set SEED_TEST_DATA=true in your environment.
    seed()
