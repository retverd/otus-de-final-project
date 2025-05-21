from os import getenv
from bs4 import BeautifulSoup
import dagster as dg
import psycopg2
import requests

# Константа с названием таблицы
CASH_EXCHANGE_RATES_TABLE = 'public.cash_exchange_rates'
SITE_NAME = 'ligovka.ru'

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
                cur.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS {CASH_EXCHANGE_RATES_TABLE} (
                        rid uuid NOT NULL DEFAULT gen_random_uuid(),
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        exchange_name VARCHAR(255) NOT NULL,
                        currency_code VARCHAR(6) NOT NULL,
                        purchase_rate NUMERIC NOT NULL,
                        sale_rate NUMERIC NOT NULL
                    );
                    '''
                )
                cur.execute(
                    f'INSERT INTO {CASH_EXCHANGE_RATES_TABLE} (exchange_name, currency_code, purchase_rate, sale_rate) VALUES (%s, %s, %s, %s)',
                    (SITE_NAME, 'USDRUB', purchase, sale)
                )
                conn.commit()
                context.log.info(f'Новый курс USDRUB от {SITE_NAME} добавлен в базу данных')
    except Exception as e:
        raise Exception(f"Ошибка при работе с PostgreSQL: {str(e)}")

    return dg.MaterializeResult(
        metadata={
            "purchase": dg.MetadataValue.float(purchase),
            "sale": dg.MetadataValue.float(sale),
        }
    )

# Расписание для регулярного обновления курса USDRUB
# Задание выполняется каждые три часа для получения актуальных данных о курсе валюты
update_schedule = dg.ScheduleDefinition(
    name="update_usd_rate_job",
    target=dg.AssetSelection.keys("fetch_usd_rate_from_ligovka"),
    cron_schedule="0 */3 * * *",
)


# Создаем Definitions с зарегистрированными активами
defs = dg.Definitions(
    assets=[fetch_usd_rate_from_ligovka],
    schedules=[update_schedule],
    # resources={"postgres": postgres}
)