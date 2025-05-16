# Выпускной проект курса "Data Engineer" от OTUS

## Предварительная архитектура проекта

![Предварительная архитектура проекта](https://www.plantuml.com/plantuml/png/BOwx3S9G301xfe014lTKsGGPsyapolEB_87r2HBLNN75BP7eMNs_tDHeBvPhoppY3k3ucJVDLiyASHgMOZdJwE2IRt66aHKJoxIguJuTFbv22IvhG1FaW8vgm8C2M75px07_we5EJVEqSfcFty0YnYU_)

## Особенности реализации

Проект запускается на сервере в защищенной инфраструктуре: доступ из Интернета к серверу закрыт, у сервера есть доступ в Интернет.

### Dagster

### PostgreSQL

Официальный образ PostgreSQL 17.5-bookworm с указанием логина и пароля для администратора, а также ограничением выделенных ресурсов.

### ClickHouse

2 экземпляра ClickHouse с использованием 3 выделенных ClickHouse Keeper: 1 шард с репликацией между clickhouse-01 и clickhouse-02. Версия 25.4.

Информацию о терминологии, конфигурации и тестировании можно найти [в документации](https://clickhouse.com/docs/en/architecture/replication).

### Metabase

Официальный образ MetaBase v0.54.5.3 c хранением настроек в базе PostgreSQL.
