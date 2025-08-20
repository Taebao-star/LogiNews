-- Supabase / Postgres 스키마 초안
create table if not exists sources (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  base_url text not null,
  rss_url text,
  active boolean default true,
  created_at timestamptz default now()
);

create table if not exists articles (
  id uuid primary key default gen_random_uuid(),
  source_id uuid references sources(id),
  url text unique not null,
  title text not null,
  author text,
  published_at timestamptz,
  raw_html text,
  content text,
  view_count int,
  rank_hint int,
  thumbnail_url text,
  fetched_at timestamptz default now()
);

create table if not exists article_enrich (
  article_id uuid primary key references articles(id) on delete cascade,
  summary_kr text not null,
  keywords text[],
  section text not null,
  lang text default 'ko',
  created_at timestamptz default now()
);

create table if not exists newsletters (
  id uuid primary key default gen_random_uuid(),
  sent_at timestamptz,
  subject text,
  html text,
  item_count int
);

create table if not exists newsletter_items (
  newsletter_id uuid references newsletters(id),
  article_id uuid references articles(id),
  section text,
  ord int,
  primary key (newsletter_id, article_id)
);
