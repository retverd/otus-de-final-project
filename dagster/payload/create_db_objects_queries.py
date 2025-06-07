# Константы с названиями источников курсов
LIGOVKA_SITE_NAME = 'ligovka.ru'
CBR_SITE_NAME = 'cbr.ru'

# Константы с названиями схем в БД
STAGE_SCHEMA = 'stage'
DATA_VAULT_SCHEMA = 'data_vault'
DATA_MARKETING_SCHEMA = 'data_marketing'

# Константы с sql-процедурами для создания схем в БД
CREATE_STAGE_SCHEMA_SQL = f'CREATE SCHEMA IF NOT EXISTS {STAGE_SCHEMA};'

CREATE_DATA_VAULT_SCHEMA_SQL = f'CREATE SCHEMA IF NOT EXISTS {DATA_VAULT_SCHEMA};'

CREATE_DATA_MARKETING_SCHEMA_SQL = f'CREATE SCHEMA IF NOT EXISTS {DATA_MARKETING_SCHEMA};'

# Константы с названиями таблиц в Stage
STAGE_CASH_EXCHANGE_RATES_TABLE = f'{STAGE_SCHEMA}.cash_exchange_rates'
STAGE_CBR_EXCHANGE_RATES_TABLE = f'{STAGE_SCHEMA}.cbr_exchange_rates'

# Константы с названиями таблиц в Data Vault
HUB_CURRENCY_PAIR_TABLE = f'{DATA_VAULT_SCHEMA}.hub_currency_pair'
HUB_RATE_TYPE_TABLE = f'{DATA_VAULT_SCHEMA}.hub_rate_type'
LINK_EXCHANGE_RATE_TABLE = f'{DATA_VAULT_SCHEMA}.link_exchange_rate'
SAT_EXCHANGE_RATE_VALUE_TABLE = f'{DATA_VAULT_SCHEMA}.sat_exchange_rate_value'

# Константы с sql-процедурами для создания Stage таблиц
STAGE_CASH_EXCHANGE_RATES_TABLE_SQL = f'''
CREATE TABLE IF NOT EXISTS {STAGE_CASH_EXCHANGE_RATES_TABLE} (
    rid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exchange_name VARCHAR(255) NOT NULL,
    currency_code VARCHAR(6) NOT NULL,
    purchase_rate NUMERIC NOT NULL,
    sale_rate NUMERIC NOT NULL
);
'''

STAGE_CBR_EXCHANGE_RATES_TABLE_SQL = f'''
CREATE TABLE IF NOT EXISTS {STAGE_CBR_EXCHANGE_RATES_TABLE} (
    rid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exchange_name VARCHAR(255) NOT NULL,
    currency_code VARCHAR(6) NOT NULL,
    rate_date DATE NOT NULL,
    rate NUMERIC NOT NULL
);
'''

# Константы с sql-процедурами для создания Data Vault таблиц
HUB_CURRENCY_PAIR_SQL = f'''
CREATE TABLE IF NOT EXISTS {HUB_CURRENCY_PAIR_TABLE} (
    currency_pair_hk CHAR(32) PRIMARY KEY,
    currency_pair_id VARCHAR(10),
    load_date TIMESTAMPTZ,
    record_source VARCHAR(100)
);
'''

HUB_RATE_TYPE_SQL = f'''
CREATE TABLE IF NOT EXISTS {HUB_RATE_TYPE_TABLE} (
    rate_type_hk CHAR(32) PRIMARY KEY,
    rate_type_id VARCHAR(20),
    load_date TIMESTAMPTZ,
    record_source VARCHAR(100)
);
'''

LINK_EXCHANGE_RATE_SQL = f'''
CREATE TABLE IF NOT EXISTS {LINK_EXCHANGE_RATE_TABLE} (
    link_hk CHAR(32) PRIMARY KEY,
    currency_pair_hk CHAR(32),
    rate_type_hk CHAR(32),
    load_date TIMESTAMPTZ,
    record_source VARCHAR(100),
    FOREIGN KEY (currency_pair_hk) REFERENCES {HUB_CURRENCY_PAIR_TABLE}(currency_pair_hk),
    FOREIGN KEY (rate_type_hk) REFERENCES {HUB_RATE_TYPE_TABLE}(rate_type_hk)
);
'''

SAT_EXCHANGE_RATE_VALUE_SQL = f'''
CREATE TABLE IF NOT EXISTS {SAT_EXCHANGE_RATE_VALUE_TABLE} (
    exchange_rate_hk CHAR(32) PRIMARY KEY,
    link_hk CHAR(32),
    rate_value DECIMAL(20,6),
    rate_date DATE,
    rate_timestamp TIMESTAMPTZ,
    load_date TIMESTAMPTZ,
    record_source VARCHAR(100),
    FOREIGN KEY (link_hk) REFERENCES {LINK_EXCHANGE_RATE_TABLE}(link_hk)
);
'''
# Константы с sql-процедурами для создания Data Marketing представлений
VW_EXCHANGE_RATE_VALUES_SQL = f'''
CREATE OR REPLACE VIEW {DATA_MARKETING_SCHEMA}.vw_exchange_rate_value AS
SELECT
	vals.record_source as source,
	hcp.currency_pair_id as currency_pair,
	hrt.rate_type_id as rate_type,
	vals.rate_value as rate,
	vals.rate_date,
	vals.rate_timestamp
FROM {SAT_EXCHANGE_RATE_VALUE_TABLE} as vals
LEFT JOIN {LINK_EXCHANGE_RATE_TABLE} ler ON ler.link_hk = vals.link_hk
LEFT JOIN {HUB_CURRENCY_PAIR_TABLE} hcp ON hcp.currency_pair_hk = ler.currency_pair_hk
LEFT JOIN {HUB_RATE_TYPE_TABLE} hrt ON hrt.rate_type_hk = ler.rate_type_hk
ORDER BY vals.rate_date DESC, vals.rate_timestamp DESC;
'''
