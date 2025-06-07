from dagster import ScheduleDefinition, AssetSelection

# Расписание для регулярного обновления курса USDRUB с сайта ligovka.ru
# Задание выполняется каждые три часа для получения актуальных данных о курсе валюты
update_schedule = ScheduleDefinition(
    name="update_usd_rate_job",
    target=AssetSelection.keys("fetch_usd_rate_from_ligovka"),
    cron_schedule="0 */3 * * *",
)

# Расписание для получения курса USDRUB на завтра с ЦБ РФ
# Задание выполняется каждый день в 16:00 для получения актуальных данных о курсе валюты на завтра
cbr_update_schedule = ScheduleDefinition(
    name="update_cbr_usd_rate_job",
    target=AssetSelection.keys("fetch_usd_rate_from_cbr"),
    cron_schedule="0 16 * * *",
)