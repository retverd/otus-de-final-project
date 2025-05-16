import pandas as pd
import dagster as dg

@dg.asset
def processed_data():
    # Читаем данные из CSV
    df = pd.read_csv("data/sample_data.csv")

    # Добавляю столбец age_group на основе значения age
    df["age_group"] = pd.cut(
        df["age"], bins=[0, 30, 40, 100], labels=["Young", "Middle", "Senior"]
    )

    # Сохраняю обработанные данные
    df.to_csv("data/processed_data.csv", index=False)
    return "Data loaded successfully"

# Создаем Definitions с зарегистрированными активами
defs = dg.Definitions(assets=[processed_data])