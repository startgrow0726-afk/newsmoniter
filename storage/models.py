import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    BigInteger,
    ForeignKey,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Index,
    Date
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, INT4RANGE
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    pw_hash = Column(Text, nullable=False)
    tz = Column(Text, nullable=False, default='Asia/Seoul')
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)

class UserPrefs(Base):
    __tablename__ = 'user_prefs'
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    quiet_hours = Column(INT4RANGE)
    severity_min = Column(Text, nullable=False, default='LOW')
    source_weights = Column(JSONB, nullable=False, default={})
    topic_weights = Column(JSONB, nullable=False, default={})
    company_weights = Column(JSONB, nullable=False, default={})
    user = relationship("User")

class Market(Base):
    __tablename__ = 'markets'
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    timezone = Column(Text, nullable=False)
    open_time = Column(String, nullable=False)
    close_time = Column(String, nullable=False)
    country_code = Column(String(2))

class Company(Base):
    __tablename__ = 'companies'
    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    tickers = Column(ARRAY(Text), nullable=False, default=[])
    aliases = Column(ARRAY(Text), nullable=False, default=[])
    context = Column(ARRAY(Text), nullable=False, default=[])
    negative = Column(ARRAY(Text), nullable=False, default=[])
    country = Column(Text)
    market_id = Column(Integer, ForeignKey('markets.id'))
    market = relationship("Market")

class UserWatchlist(Base):
    __tablename__ = 'user_watchlist'
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    company_id = Column(BigInteger, ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)

class Source(Base):
    __tablename__ = 'sources'
    id = Column(BigInteger, primary_key=True)
    domain = Column(Text, unique=True, nullable=False)
    trust = Column(Float, nullable=False, default=0.700)

class Feed(Base):
    __tablename__ = 'feeds'
    id = Column(BigInteger, primary_key=True)
    url = Column(Text, unique=True, nullable=False)
    source_id = Column(BigInteger, ForeignKey('sources.id'))
    topic = Column(Text)
    active = Column(Boolean, nullable=False, default=True)
    etag = Column(Text)
    last_modified = Column(Text)
    last_checked = Column(DateTime(timezone=True))
    source = relationship("Source")

class Article(Base):
    __tablename__ = 'articles'
    id = Column(BigInteger, primary_key=True)
    url = Column(Text, nullable=False, unique=True)
    canonical_url = Column(Text)
    url_hash = Column(BigInteger, nullable=False, index=True)
    source_domain = Column(Text, nullable=False)
    source_id = Column(BigInteger, ForeignKey('sources.id'))
    title = Column(Text)
    body = Column(Text)
    lang = Column(String(5))
    published_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    source = relationship("Source")

class ArticleEntity(Base):
    __tablename__ = 'article_entities'
    article_id = Column(BigInteger, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True)
    company_id = Column(BigInteger, ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True)
    confidence = Column(Float, nullable=False)
    matched = Column(Text)
    article = relationship("Article")
    company = relationship("Company")

class ArticleMeta(Base):
    __tablename__ = 'article_meta'
    article_id = Column(BigInteger, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True)
    category = Column(Text, nullable=False)
    topic_tags = Column(ARRAY(Text), nullable=False, default=[])
    related_event = Column(Text)
    sentiment = Column(Float, nullable=False, default=0.0)
    positivity_pct = Column(Integer, nullable=False)
    accuracy_pct = Column(Integer, nullable=False)
    importance_pct = Column(Integer, nullable=False, index=True)
    impact_level = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    volatility_hint = Column(Text)
    article = relationship("Article")

class ArticleLink(Base):
    __tablename__ = 'article_links'
    article_id = Column(BigInteger, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True)
    link_type = Column(Text, nullable=False, primary_key=True) # 'related' | 'tech'
    url = Column(Text, nullable=False, primary_key=True)
    article = relationship("Article")

class Cluster(Base):
    __tablename__ = 'clusters'
    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False, index=True)
    article_count = Column(Integer, nullable=False, default=1)

class ClusterArticle(Base):
    __tablename__ = 'cluster_articles'
    cluster_id = Column(Text, ForeignKey('clusters.id', ondelete='CASCADE'), primary_key=True)
    article_id = Column(BigInteger, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True)
    rank = Column(Integer, nullable=False)
    cluster = relationship("Cluster")
    article = relationship("Article")

class Delivery(Base):
    __tablename__ = 'deliveries'
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    article_id = Column(BigInteger, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True)
    cluster_id = Column(Text)
    rank = Column(Integer, nullable=False)
    seen = Column(Boolean, nullable=False, default=False)
    clicked = Column(Boolean, nullable=False, default=False)
    saved = Column(Boolean, nullable=False, default=False)
    delivered_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    __table_args__ = (Index('idx_deliveries_user_time', 'user_id', 'delivered_at'),)

class CompanyContext(Base):
    __tablename__ = 'company_context'
    company_id = Column(BigInteger, ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True)
    customer_score = Column(Integer)
    supply_score = Column(Integer)
    policy_risk_pct = Column(Integer)
    competition_pct = Column(Integer)
    company_context_score = Column(Integer) # New column for overall score
    updated_at = Column(DateTime(timezone=True))
    company = relationship("Company")

class CompanyRelation(Base):
    __tablename__ = 'company_relations'
    company_id = Column(BigInteger, ForeignKey('companies.id'), primary_key=True)
    counterparty_id = Column(BigInteger, ForeignKey('companies.id'), primary_key=True)
    relation_type = Column(Text, primary_key=True) # 'customer'|'partner'|'supplier'|'competitor'
    weight = Column(Float)
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))

class IntradayExplain(Base):
    __tablename__ = 'intraday_explain'
    ticker = Column(Text, primary_key=True)
    date = Column(Date, primary_key=True)
    move_pct = Column(Float)
    vwap = Column(Float)
    sector_corr = Column(Float)
    index_corr = Column(Float)
    cause_company_pct = Column(Integer)
    cause_sector_pct = Column(Integer)
    cause_macro_pct = Column(Integer)
    cause_flow_pct = Column(Integer)
    sentiment_label = Column(Text)
    one_day_view = Column(Text)
    short_term_view = Column(Text)
    mid_long_view = Column(Text)
    evidence = Column(JSONB)
    generated_at = Column(DateTime(timezone=True))

class DailyRecap(Base):
    __tablename__ = 'daily_recap'
    ticker = Column(Text, primary_key=True)
    date = Column(Date, primary_key=True)
    top_events = Column(JSONB)
    perf_vs_sector = Column(Float)
    perf_vs_index = Column(Float)
    recap_text = Column(Text)
    watch_points = Column(ARRAY(Text))
    risk_notes = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True))

class ShortInterest(Base):
    __tablename__ = 'short_interest'
    date = Column(Date, primary_key=True)
    ticker = Column(Text, primary_key=True)
    short_volume = Column(BigInteger, nullable=False)
    total_volume = Column(BigInteger, nullable=False)
    short_volume_ratio = Column(Float, nullable=False)
    __table_args__ = (Index('ix_short_interest_ticker_date', 'ticker', 'date'),)