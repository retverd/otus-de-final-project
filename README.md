# Выпускной проект курса "Data Engineer" от OTUS

## Предварительная архитектура проекта

![Предварительная архитектура проекта](https://www.plantuml.com/plantuml/png/BOqx3i8m341tJW47QBqpzIR8n6vZb3YHFt1zYiJqtl2ajtcWHVPskOcMbiJN6Z7z3c3uMG-9cizqjZ8qM6CjeuDnlDa8HgGlnCikYcsPDbvS0entXyf83Xr5WGGFm-xm3nvefKgSbiRh_BqtLZhv1G00)

## Особенности реализации

### Dagster

### PostgreSQL

### ClickHouse

2 экземпляра ClickHouse с использованием 3 выделенных ClickHouse Keeper: 1 шард с репликацией между clickhouse-01 и clickhouse-02.

Во избежание проблем с незапланированным изменением версий ClickHouse и ClickHouse Keeper при сохранении версии хранилища версии указаны явно в файле .env.

Информацию о терминологии, конфигурации и тестировании можно найти [в документации](https://clickhouse.com/docs/en/architecture/replication).

### Metabase
