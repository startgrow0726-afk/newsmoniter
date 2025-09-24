-- 사용자
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    pw_hash TEXT NOT NULL,
    tz TEXT NOT NULL DEFAULT 'Asia/Seoul',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_prefs (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    quiet_hours INT4RANGE, -- 예: [23,6)
    severity_min TEXT NOT NULL DEFAULT 'LOW', -- LOW|MEDIUM|HIGH
    source_weights JSONB NOT NULL DEFAULT '{}', -- domain->[-1.0..+1.0]
    topic_weights JSONB NOT NULL DEFAULT '{}', -- topic->[-1.0..+1.0]
    company_weights JSONB NOT NULL DEFAULT '{}' -- company_id->[-1.0..+1.0]
);

-- 기업/워치리스트
CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    tickers TEXT[] NOT NULL DEFAULT '{}',
    aliases TEXT[] NOT NULL DEFAULT '{}',
    context TEXT[] NOT NULL DEFAULT '{}',
    negative TEXT[] NOT NULL DEFAULT '{}',
    country TEXT
);
CREATE UNIQUE INDEX idx_companies_name ON companies (lower(name));

CREATE TABLE user_watchlist (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, company_id)
);

-- 소스/피드
CREATE TABLE sources (
    id BIGSERIAL PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    trust NUMERIC(4,3) NOT NULL DEFAULT 0.700
);

CREATE TABLE feeds (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    source_id BIGINT REFERENCES sources(id),
    topic TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    etag TEXT,
    last_modified TEXT,
    last_checked TIMESTAMPTZ
);

-- 기사/엔리치
CREATE TABLE articles (
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
CREATE INDEX idx_articles_pub ON articles (published_at DESC);
CREATE INDEX idx_articles_urlhash ON articles (url_hash);

CREATE TABLE article_entities (
    article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE,
    confidence NUMERIC(3,2) NOT NULL,
    matched TEXT,
    PRIMARY KEY(article_id, company_id)
);

CREATE TABLE article_meta (
    article_id BIGINT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    topic_tags TEXT[] NOT NULL DEFAULT '{}',
    related_event TEXT,
    sentiment NUMERIC(4,2) NOT NULL DEFAULT 0.0, -- [-1..+1]
    positivity_pct INT NOT NULL, -- [0..100]
    accuracy_pct INT NOT NULL, -- [50..100]
    importance_pct INT NOT NULL, -- [0..100]
    impact_level TEXT NOT NULL, -- '작음'|'보통'|'큼'
    severity TEXT NOT NULL, -- LOW|MEDIUM|HIGH
    volatility_hint TEXT
);

CREATE TABLE article_links (
    article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL, -- 'related' | 'tech'
    url TEXT NOT NULL,
    PRIMARY KEY(article_id, link_type, url)
);

-- 사건 클러스터
CREATE TABLE clusters (
    id TEXT PRIMARY KEY, -- cluster_id
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    article_count INT NOT NULL DEFAULT 1
);

CREATE TABLE cluster_articles (
    cluster_id TEXT REFERENCES clusters(id) ON DELETE CASCADE,
    article_id BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    rank INT NOT NULL,
    PRIMARY KEY(cluster_id, article_id)
);

-- 개인화 제공/행동
CREATE TABLE deliveries (
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
CREATE INDEX idx_deliveries_user_time ON deliveries (user_id, delivered_at DESC);