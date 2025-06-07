from dagster import Definitions
from .assets import fetch_usd_rate_from_ligovka, fetch_usd_rate_from_cbr
from .schedules import update_schedule, cbr_update_schedule

# Создаем Definitions с зарегистрированными активами
defs = Definitions(
    assets=[
        fetch_usd_rate_from_ligovka, 
        fetch_usd_rate_from_cbr,
    ],
    schedules=[update_schedule, cbr_update_schedule],
    # resources={"postgres": postgres}
)