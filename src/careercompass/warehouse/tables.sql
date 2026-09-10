-- CareerCompass BR — Schema do Data Warehouse (DuckDB)
-- Rodado automaticamente pelo warehouse/duckdb.py na inicialização

-- ── Staging ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staging_jobs (
    fonte           VARCHAR NOT NULL,
    id              VARCHAR NOT NULL,
    titulo          VARCHAR NOT NULL,
    empresa         VARCHAR,
    empresa_id      VARCHAR,
    cidade          VARCHAR,
    estado          VARCHAR,
    url             VARCHAR,
    modalidade      VARCHAR,
    publicado_em    VARCHAR,
    salario_min     DOUBLE,
    salario_max     DOUBLE,
    salario_moeda   VARCHAR,
    salario_raw     VARCHAR,
    stack_matches   VARCHAR[],
    stack_skills    VARCHAR[],
    senioridade     VARCHAR,
    descricao       VARCHAR,
    loaded_at       TIMESTAMP DEFAULT now(),
    PRIMARY KEY (fonte, id)
);

-- ── Dimensões ──────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS seq_dim_company START 1;

CREATE TABLE IF NOT EXISTS dim_company (
    company_id  INTEGER DEFAULT nextval('seq_dim_company'),
    empresa     VARCHAR NOT NULL UNIQUE,
    empresa_orig VARCHAR,
    PRIMARY KEY (company_id)
);

CREATE SEQUENCE IF NOT EXISTS seq_dim_location START 1;

CREATE TABLE IF NOT EXISTS dim_location (
    location_id INTEGER DEFAULT nextval('seq_dim_location'),
    cidade      VARCHAR NOT NULL,
    estado      VARCHAR,
    uf          VARCHAR,
    PRIMARY KEY (location_id),
    UNIQUE (cidade, estado)
);

CREATE SEQUENCE IF NOT EXISTS seq_dim_skill START 1;

CREATE TABLE IF NOT EXISTS dim_skill (
    skill_id    INTEGER DEFAULT nextval('seq_dim_skill'),
    skill_name  VARCHAR NOT NULL UNIQUE,
    categoria   VARCHAR,
    PRIMARY KEY (skill_id)
);

-- ── Fatos ──────────────────────────────────────────────────────────────
CREATE SEQUENCE IF NOT EXISTS seq_fact_job START 1;

CREATE TABLE IF NOT EXISTS fact_job (
    job_id          INTEGER DEFAULT nextval('seq_fact_job'),
    fonte           VARCHAR NOT NULL,
    url_original    VARCHAR,
    titulo          VARCHAR NOT NULL,
    senioridade     VARCHAR,
    modalidade      VARCHAR,
    publicado_em    VARCHAR,
    empresa_id      INTEGER REFERENCES dim_company(company_id),
    location_id     INTEGER REFERENCES dim_location(location_id),
    categoria_principal VARCHAR,
    salario_min     DOUBLE,
    salario_max     DOUBLE,
    salario_moeda   VARCHAR,
    salario_raw     VARCHAR,
    loaded_at       TIMESTAMP DEFAULT now(),
    PRIMARY KEY (job_id),
    UNIQUE (fonte, url_original)
);

CREATE TABLE IF NOT EXISTS fact_job_skill (
    job_id      INTEGER REFERENCES fact_job(job_id),
    skill_id    INTEGER REFERENCES dim_skill(skill_id),
    PRIMARY KEY (job_id, skill_id)
);

CREATE SEQUENCE IF NOT EXISTS seq_fact_salary START 1;

CREATE TABLE IF NOT EXISTS fact_salary (
    salary_id       INTEGER DEFAULT nextval('seq_fact_salary'),
    job_id          INTEGER REFERENCES fact_job(job_id),
    salario_min     DOUBLE,
    salario_max     DOUBLE,
    salario_moeda   VARCHAR,
    PRIMARY KEY (salary_id),
    UNIQUE (job_id)
);
