from dagster import Definitions
from .assets import fetch_usd_rate_from_ligovka, fetch_usd_rate_from_cbr, move_cbr_rates_to_dv, move_ligovka_rates_to_dv
from .schedules import update_schedule, cbr_update_schedule

# Создаем Definitions с зарегистрированными активами
defs = Definitions(
    assets=[
        fetch_usd_rate_from_ligovka, 
        fetch_usd_rate_from_cbr,
        move_cbr_rates_to_dv,
        move_ligovka_rates_to_dv
    ],
    schedules=[update_schedule, cbr_update_schedule],
    # resources={"postgres": postgres}
)
