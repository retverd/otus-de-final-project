from os import getenv
from bs4 import BeautifulSoup
import dagster as dg
import psycopg2
import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# Константы с названиями таблиц
CASH_EXCHANGE_RATES_TABLE = 'stage.cash_exchange_rates'
CBR_EXCHANGE_RATES_TABLE = 'stage.cbr_exchange_rates'
LIGOVKA_SITE_NAME = 'ligovka.ru'
CBR_SITE_NAME = 'cbr.ru'

# Константы с sql-процедурами для создания таблиц
CASH_EXCHANGE_RATES_TABLE_SQL = f'''
CREATE TABLE IF NOT EXISTS {CASH_EXCHANGE_RATES_TABLE} (
    rid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exchange_name VARCHAR(255) NOT NULL,
    currency_code VARCHAR(6) NOT NULL,
    purchase_rate NUMERIC NOT NULL,
    sale_rate NUMERIC NOT NULL
);
'''

CBR_EXCHANGE_RATES_TABLE_SQL = f'''
CREATE TABLE IF NOT EXISTS {CBR_EXCHANGE_RATES_TABLE} (
    rid uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exchange_name VARCHAR(255) NOT NULL,
    currency_code VARCHAR(6) NOT NULL,
    rate_date DATE NOT NULL,
    rate NUMERIC NOT NULL
);
'''

# TODO: переделать на использование ресурса postgres
# @dg.resource(config_schema={
#     'host': dg.Field(str, default_value=getenv('POSTGRES_HOST', 'localhost')),
#     'port': dg.Field(int, default_value=int(getenv('POSTGRES_PORT', '5432'))),
#     'db': dg.Field(str, default_value=getenv('DATA_DB_NAME', 'data_db')),
#     'user': dg.Field(str, default_value=getenv('DATA_DB_USER', 'data_user')),
#     'password': dg.Field(str, default_value=getenv('DATA_DB_PASS', 'D@tA3RsecreTpaSsw0rD351')),
# })
# def postgres(init_context):
#     '''Предоставляет psycopg2-соединение с PostgreSQL.'''
#     conn = psycopg2.connect(
#         host=init_context.resource_config['host'],
#         port=init_context.resource_config['port'],
#         dbname=init_context.resource_config['db'],
#         user=init_context.resource_config['user'],
#         password=init_context.resource_config['password'],
#     )
#     try:
#         yield conn
#     finally:
#         conn.close()

@dg.asset(
    compute_kind="postgres",
    group_name="ingestion",
)
def fetch_usd_rate_from_ligovka(context):
    '''Получает курсы покупки и продажи USD для сумм ≥1000 рублей с сайта ligovka.ru и сохраняет в таблицу PostgreSQL'''
    url = 'https://ligovka.ru/'
    context.log.info(f'Получение курса USDRUB с {url}')
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Не удалось загрузить страницу, код ответа: {response.status_code}')
    soup = BeautifulSoup(response.text, 'html.parser')
    usd_links = soup.find_all('a', href=lambda href: href and '/detailed/usd?tab=1000' in href)
    if len(usd_links) < 2:
        raise Exception('Не удалось найти курс USD для сумм ≥1000 рублей на странице')
    purchase = float(usd_links[0].get_text(strip=True).replace(',', '.'))
    sale = float(usd_links[1].get_text(strip=True).replace(',', '.'))
    context.log.info(f'Найдены курсы USD – покупка: {purchase}, продажа: {sale}')

    # Получаем параметры подключения из переменных окружения
    db_params = {
        "host": getenv("POSTGRES_HOST"),
        "port": getenv("POSTGRES_PORT"),
        "database": getenv("DATA_DB_NAME"),
        "user": getenv("DATA_DB_USER"),
        "password": getenv("DATA_DB_PASS")
    }

    try:
        # Подключаемся к PostgreSQL
        # conn = context.resources.postgres
        with psycopg2.connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Создаем таблицу с правильными типами данных
                cur.execute(CASH_EXCHANGE_RATES_TABLE_SQL)
                cur.execute(
                    f'INSERT INTO {CASH_EXCHANGE_RATES_TABLE} (exchange_name, currency_code, purchase_rate, sale_rate) VALUES (%s, %s, %s, %s)',
                    (LIGOVKA_SITE_NAME, 'USDRUB', purchase, sale)
                )
                conn.commit()
                context.log.info(f'Новый курс USDRUB от {LIGOVKA_SITE_NAME} добавлен в таблицу {CASH_EXCHANGE_RATES_TABLE}')
    except Exception as e:
        raise Exception(f"Ошибка при работе с PostgreSQL: {str(e)}")

    return dg.MaterializeResult(
        metadata={
            "purchase": dg.MetadataValue.float(purchase),
            "sale": dg.MetadataValue.float(sale),
        }
    )

@dg.asset(
    compute_kind="postgres",
    group_name="ingestion",
)
def fetch_usd_rate_from_cbr(context):
    '''Получает курс USD на завтра с сайта ЦБ РФ и сохраняет в таблицу PostgreSQL'''
    # Получаем дату на завтра
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime('%d/%m/%Y')
    
    url = f'https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date_str}&date_req2={date_str}&VAL_NM_RQ=R01235'
    context.log.info(f'Получение курса USDRUB на {date_str} с {url}')
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            context.log.error(f'Не удалось загрузить страницу, код ответа: {response.status_code}')
            return dg.MaterializeResult()
            
        # Парсим XML ответ
        root = ET.fromstring(response.text)
        if not root.findall('.//Record'):
            context.log.warning(f'Курс на {date_str} не установлен')
            return dg.MaterializeResult()
            
        # Получаем курс
        rate = float(root.find('.//Value').text.replace(',', '.'))
        context.log.info(f'Найден курс USD на {date_str}: {rate}')

        # Получаем параметры подключения из переменных окружения
        db_params = {
            "host": getenv("POSTGRES_HOST"),
            "port": getenv("POSTGRES_PORT"),
            "database": getenv("DATA_DB_NAME"),
            "user": getenv("DATA_DB_USER"),
            "password": getenv("DATA_DB_PASS")
        }

        # Подключаемся к PostgreSQL
        with psycopg2.connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Создаем таблицу с правильными типами данных
                cur.execute(CBR_EXCHANGE_RATES_TABLE_SQL)
                cur.execute(
                    f'INSERT INTO {CBR_EXCHANGE_RATES_TABLE} (exchange_name, currency_code, rate_date, rate) VALUES (%s, %s, %s, %s)',
                    (CBR_SITE_NAME, 'USDRUB', tomorrow.date(), rate)
                )
                conn.commit()
                context.log.info(f'Новый курс USDRUB от {CBR_SITE_NAME} на {date_str} добавлен в таблицу {CBR_EXCHANGE_RATES_TABLE}')
                
        return dg.MaterializeResult(
            metadata={
                "rate": dg.MetadataValue.float(rate),
                "date": dg.MetadataValue.text(date_str),
            }
        )
    except Exception as e:
        context.log.error(f"Ошибка при получении курса с CBR: {str(e)}")
        return dg.MaterializeResult()

# Расписание для регулярного обновления курса USDRUB
# Задание выполняется каждые три часа для получения актуальных данных о курсе валюты
update_schedule = dg.ScheduleDefinition(
    name="update_usd_rate_job",
    target=dg.AssetSelection.keys("fetch_usd_rate_from_ligovka"),
    cron_schedule="0 */3 * * *",
)

# Расписание для получения курса USDRUB на завтра с ЦБ РФ
# Задание выполняется каждый день в 16:00 для получения актуальных данных о курсе валюты на завтра
cbr_update_schedule = dg.ScheduleDefinition(
    name="update_cbr_usd_rate_job",
    target=dg.AssetSelection.keys("fetch_usd_rate_from_cbr"),
    cron_schedule="0 16 * * *",
)

# Создаем Definitions с зарегистрированными активами
defs = dg.Definitions(
    assets=[fetch_usd_rate_from_ligovka, fetch_usd_rate_from_cbr],
    schedules=[update_schedule, cbr_update_schedule],
    # resources={"postgres": postgres}
)