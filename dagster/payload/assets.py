from os import getenv
from bs4 import BeautifulSoup
import dagster as dg
from psycopg2 import connect
from requests import get
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from payload.create_tables_queries import *
from payload.move_to_dv_queries import *

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
#     conn = connect(
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
    response = get(url)
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
        with connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Создаем схему Stage, если она не существует
                cur.execute(CREATE_STAGE_SCHEMA_SQL)

                # Создаем таблицу с правильными типами данных, если она не существует
                cur.execute(STAGE_CASH_EXCHANGE_RATES_TABLE_SQL)
                cur.execute(
                    f'INSERT INTO {STAGE_CASH_EXCHANGE_RATES_TABLE} (exchange_name, currency_code, purchase_rate, sale_rate) VALUES (%s, %s, %s, %s)',
                    (LIGOVKA_SITE_NAME, 'USDRUB', purchase, sale)
                )
                conn.commit()
                context.log.info(f'Новый курс USDRUB от {LIGOVKA_SITE_NAME} добавлен в таблицу {STAGE_CASH_EXCHANGE_RATES_TABLE}')
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
        response = get(url)
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
        with connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Создаем схему Stage, если она не существует
                cur.execute(CREATE_STAGE_SCHEMA_SQL)

                # Создаем таблицу с правильными типами данных, если она не существует
                cur.execute(STAGE_CBR_EXCHANGE_RATES_TABLE_SQL)
                cur.execute(
                    f'INSERT INTO {STAGE_CBR_EXCHANGE_RATES_TABLE} (exchange_name, currency_code, rate_date, rate) VALUES (%s, %s, %s, %s)',
                    (CBR_SITE_NAME, 'USDRUB', tomorrow.date(), rate)
                )
                conn.commit()
                context.log.info(f'Новый курс USDRUB от {CBR_SITE_NAME} на {date_str} добавлен в таблицу {STAGE_CBR_EXCHANGE_RATES_TABLE}')
                
        return dg.MaterializeResult(
            metadata={
                "rate": dg.MetadataValue.float(rate),
                "date": dg.MetadataValue.text(date_str),
            }
        )
    except Exception as e:
        context.log.error(f"Ошибка при получении курса с CBR: {str(e)}")
        return dg.MaterializeResult()

@dg.asset(
    compute_kind="postgres",
    group_name="transform",
    deps=["fetch_usd_rate_from_cbr"],
    automation_condition=dg.AutomationCondition.eager(),
)
def move_cbr_rates_to_dv(context):
    '''Загружает данные из staging.cbr_exchange_rates в Data Vault структуру'''
    
    db_params = {
        "host": getenv("POSTGRES_HOST"),
        "port": getenv("POSTGRES_PORT"),
        "database": getenv("DATA_DB_NAME"),
        "user": getenv("DATA_DB_USER"),
        "password": getenv("DATA_DB_PASS")
    }

    try:
        with connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Создаем схему Data Vault, если она не существует
                cur.execute(CREATE_DATA_VAULT_SCHEMA_SQL)
                
                # Создаем Hub-таблицы, если они не существуют
                cur.execute(HUB_CURRENCY_PAIR_SQL)
                cur.execute(HUB_RATE_TYPE_SQL)

                # Создаем Link-таблицу, если она не существует
                cur.execute(LINK_EXCHANGE_RATE_SQL)

                # Создаем Satellite-таблицу, если она не существует
                cur.execute(SAT_EXCHANGE_RATE_VALUE_SQL)

                # Вставляем данные из staging в Data Vault
                # TODO: проверить, сколько строк реально загружается в таблицу Satellite и доработать вывод в лог
                cur.execute(MOVE_CBR_RATES_TO_DV)
                
                conn.commit()
                context.log.info(f"Данные из {CBR_SITE_NAME} успешно загружены в Data Vault")

    except Exception as e:
        raise Exception(f"Ошибка при загрузке данных в Data Vault: {str(e)}")

    return dg.MaterializeResult()

@dg.asset(
    compute_kind="postgres",
    group_name="transform",
    deps=["fetch_usd_rate_from_ligovka"],
    automation_condition=dg.AutomationCondition.eager(),
)
def move_ligovka_rates_to_dv(context):
    '''Загружает данные из stage.cash_exchange_rates в Data Vault структуру'''
    
    db_params = {
        "host": getenv("POSTGRES_HOST"),
        "port": getenv("POSTGRES_PORT"),
        "database": getenv("DATA_DB_NAME"),
        "user": getenv("DATA_DB_USER"),
        "password": getenv("DATA_DB_PASS")
    }

    try:
        with connect(**db_params) as conn:
            with conn.cursor() as cur:
                # Создаем схему Data Vault, если она не существует
                cur.execute(CREATE_DATA_VAULT_SCHEMA_SQL)
                
                # Создаем Hub-таблицы, если они не существуют
                cur.execute(HUB_CURRENCY_PAIR_SQL)
                cur.execute(HUB_RATE_TYPE_SQL)

                # Создаем Link-таблицу, если она не существует
                cur.execute(LINK_EXCHANGE_RATE_SQL)

                # Создаем Satellite-таблицу, если она не существует
                cur.execute(SAT_EXCHANGE_RATE_VALUE_SQL)

                # Вставляем данные из staging в Data Vault
                # TODO: проверить, сколько строк реально загружается в таблицу Satellite и доработать вывод в лог
                cur.execute(MOVE_LIGOVKA_RATES_TO_DV)
                
                conn.commit()
                context.log.info(f"Данные из {LIGOVKA_SITE_NAME} успешно загружены в Data Vault")

    except Exception as e:
        raise Exception(f"Ошибка при загрузке данных в Data Vault: {str(e)}")

    return dg.MaterializeResult()
