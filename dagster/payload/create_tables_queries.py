# Константы с названиями источников курсов
LIGOVKA_SITE_NAME = 'ligovka.ru'
CBR_SITE_NAME = 'cbr.ru'

# Константы с названиями таблиц в Stage
STAGE_CASH_EXCHANGE_RATES_TABLE = 'stage.cash_exchange_rates'
STAGE_CBR_EXCHANGE_RATES_TABLE = 'stage.cbr_exchange_rates'

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
