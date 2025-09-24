-- Core tables (subset necessary to start; expand later)
CREATE TABLE IF NOT EXISTS users(
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  pw_hash TEXT NOT NULL,
  tz TEXT NOT NULL DEFAULT 'Asia/Seoul',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS user_prefs(
  user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  quiet_hours INT4RANGE,
  severity_min TEXT NOT NULL DEFAULT 'LOW',
  source_weights JSONB NOT NULL DEFAULT '{}',
  topic_weights  JSONB NOT NULL DEFAULT '{}',
  company_weights JSONB NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS companies(
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  tickers TEXT[] NOT NULL DEFAULT '{}',
  aliases TEXT[] NOT NULL DEFAULT '{}',
  context TEXT[] NOT NULL DEFAULT '{}',
  negative TEXT[] NOT NULL DEFAULT '{}',
  country TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_name ON companies (lower(name));
CREATE TABLE IF NOT EXISTS user_watchlist(
  user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
  company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id, company_id)
);
CREATE TABLE IF NOT EXISTS sources(
  id BIGSERIAL PRIMARY KEY,
  domain TEXT UNIQUE NOT NULL,
  trust NUMERIC(4,3) NOT NULL DEFAULT 0.700
);
CREATE TABLE IF NOT EXISTS feeds(
  id BIGSERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  source_id BIGINT REFERENCES sources(id),
  topic TEXT,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  etag TEXT,
  last_modified TEXT,
  last_checked TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS articles(
  id BIGSERIAL PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  canonical_url TEXT,
  url_hash BIGINT NOT NULL,
  source_domain TEXT NOT NULL,
  source_id BIGINT REFERENCES sources(id),
  title TEXT,
  body TEXT,
  lang TEXT,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_articles_pub ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_urlhash ON articles (url_hash);
CREATE TABLE IF NOT EXISTS article_entities(
  article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
  company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
  confidence NUMERIC(3,2) NOT NULL,
  matched TEXT,
  PRIMARY KEY(article_id, company_id)
);
CREATE TABLE IF NOT EXISTS article_meta(
  article_id BIGINT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  topic_tags TEXT[] NOT NULL DEFAULT '{}',
  related_event TEXT,
  sentiment NUMERIC(4,2) NOT NULL DEFAULT 0.0,
  positivity_pct INT NOT NULL,
  accuracy_pct INT NOT NULL,
  importance_pct INT NOT NULL,
  impact_level TEXT NOT NULL,
  severity TEXT NOT NULL,
  volatility_hint TEXT
);
CREATE TABLE IF NOT EXISTS article_links(
  article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
  link_type TEXT NOT NULL,
  url TEXT NOT NULL,
  PRIMARY KEY(article_id, link_type, url)
);
CREATE TABLE IF NOT EXISTS clusters(
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  severity TEXT NOT NULL,
  first_seen TIMESTAMPTZ NOT NULL,
  last_seen TIMESTAMPTZ NOT NULL,
  article_count INT NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cluster_articles(
  cluster_id TEXT REFERENCES clusters(id) ON DELETE CASCADE,
  article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
  rank INT NOT NULL,
  PRIMARY KEY(cluster_id, article_id)
);
CREATE TABLE IF NOT EXISTS deliveries(
  user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
  article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
  cluster_id TEXT,
  rank INT NOT NULL,
  seen BOOLEAN NOT NULL DEFAULT FALSE,
  clicked BOOLEAN NOT NULL DEFAULT FALSE,
  saved BOOLEAN NOT NULL DEFAULT FALSE,
  delivered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id, article_id)
);
CREATE INDEX IF NOT EXISTS idx_deliveries_user_time ON deliveries (user_id, delivered_at DESC);
