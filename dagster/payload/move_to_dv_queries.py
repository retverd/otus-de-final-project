from payload.create_tables_queries import *

START_DATE = '1900-01-01'

MOVE_CBR_RATES_TO_DV = f'''
                    WITH new_data AS (
                        SELECT DISTINCT 
                            currency_code,
                            rate_date,
                            rate,
                            timestamp
                        FROM {STAGE_CBR_EXCHANGE_RATES_TABLE}
                        WHERE timestamp > COALESCE(
                            (SELECT MAX(load_date) FROM {SAT_EXCHANGE_RATE_VALUE_TABLE} WHERE record_source = '{CBR_SITE_NAME}'),
                            '{START_DATE}'::timestamp
                        ) and exchange_name = '{CBR_SITE_NAME}'
                    ),
                    existing_currency_pairs AS (
                        SELECT 
                            currency_pair_hk,
                            currency_pair_id
                        FROM {HUB_CURRENCY_PAIR_TABLE}
                        WHERE currency_pair_id IN (SELECT currency_code FROM new_data)
                    ),
                    new_currency_pairs AS (
                        INSERT INTO {HUB_CURRENCY_PAIR_TABLE} (currency_pair_hk, currency_pair_id, load_date, record_source)
                        SELECT 
                            MD5(currency_code)::CHAR(32),
                            currency_code,
                            NOW(),
                            '{CBR_SITE_NAME}'
                        FROM new_data
                        ON CONFLICT (currency_pair_hk) DO NOTHING
                        RETURNING currency_pair_hk, currency_pair_id
                    ),
                    all_currency_pairs AS (
                        SELECT * FROM new_currency_pairs
                        UNION ALL
                        SELECT * FROM existing_currency_pairs
                    ),
                    existing_rate_types AS (
                        SELECT 
                            rate_type_hk,
                            rate_type_id
                        FROM {HUB_RATE_TYPE_TABLE}
                        WHERE record_source = '{CBR_SITE_NAME}'
                    ),
                    new_rate_types AS (
                        INSERT INTO {HUB_RATE_TYPE_TABLE}
                        VALUES
                            (MD5('reference')::CHAR(32), 'reference', NOW(), '{CBR_SITE_NAME}')
                        ON CONFLICT (rate_type_hk) DO NOTHING
                        RETURNING rate_type_hk, rate_type_id
                    ),
                    all_rate_types AS (
                        SELECT * FROM new_rate_types
                        UNION ALL
                        SELECT * FROM existing_rate_types
                    ),
                    new_links_data AS (
                        INSERT INTO data_vault.link_exchange_rate (
                            link_hk,
                            currency_pair_hk,
                            rate_type_hk,
                            load_date,
                            record_source
                        )
                        SELECT DISTINCT
                            MD5(nd.currency_code || '{CBR_SITE_NAME}' || rt.rate_type_id)::CHAR(32),
                            cp.currency_pair_hk,
                            rt.rate_type_hk,
                            NOW(),
                            '{CBR_SITE_NAME}'
                        FROM new_data nd
                        JOIN all_currency_pairs cp ON cp.currency_pair_id = nd.currency_code
                        cross JOIN all_rate_types rt
                        ON CONFLICT (link_hk) DO NOTHING
                        RETURNING link_hk, rate_type_hk
                    ),
                    old_links_data AS (
                        select
                            link_hk,
                            rate_type_hk
                        from data_vault.link_exchange_rate
                        where record_source = '{CBR_SITE_NAME}'
                    ),
                    all_links_data AS (
                        SELECT * FROM new_links_data
                        UNION ALL
                        SELECT * FROM old_links_data
                    )
                    INSERT INTO {SAT_EXCHANGE_RATE_VALUE_TABLE} (
                        exchange_rate_hk,
                        link_hk,
                        rate_value,
                        rate_date,
                        rate_timestamp,
                        load_date,
                        record_source
                    )
                    SELECT 
                        MD5(nd.currency_code || rt.rate_type_id || nd.timestamp)::CHAR(32),
                        ld.link_hk,
                        nd.rate,
                        nd.rate_date,
                        nd.timestamp,
                        NOW(),
                        '{CBR_SITE_NAME}'
                    FROM new_data nd
                    cross JOIN all_links_data ld
                    JOIN all_rate_types rt ON ld.rate_type_hk = rt.rate_type_hk;
                '''

MOVE_LIGOVKA_RATES_TO_DV = f'''
                    WITH new_data AS (
                        SELECT DISTINCT 
                            currency_code,
                            purchase_rate,
                            sale_rate,
                            timestamp
                        FROM {STAGE_CASH_EXCHANGE_RATES_TABLE}
                        WHERE timestamp > COALESCE(
                            (SELECT MAX(load_date) FROM {SAT_EXCHANGE_RATE_VALUE_TABLE} WHERE record_source = '{LIGOVKA_SITE_NAME}'),
                            '{START_DATE}'::timestamp
                        ) and exchange_name = '{LIGOVKA_SITE_NAME}'
                    ),
                    existing_currency_pairs AS (
                        SELECT 
                            currency_pair_hk,
                            currency_pair_id
                        FROM {HUB_CURRENCY_PAIR_TABLE}
                        WHERE currency_pair_id IN (SELECT currency_code FROM new_data)
                    ),
                    new_currency_pairs AS (
                        INSERT INTO {HUB_CURRENCY_PAIR_TABLE} (currency_pair_hk, currency_pair_id, load_date, record_source)
                        SELECT 
                            MD5(currency_code)::CHAR(32),
                            currency_code,
                            NOW(),
                            '{LIGOVKA_SITE_NAME}'
                        FROM new_data
                        ON CONFLICT (currency_pair_hk) DO NOTHING
                        RETURNING currency_pair_hk, currency_pair_id
                    ),
                    all_currency_pairs AS (
                        SELECT * FROM new_currency_pairs
                        UNION ALL
                        SELECT * FROM existing_currency_pairs
                    ),
                    existing_rate_types AS (
                        SELECT 
                            rate_type_hk,
                            rate_type_id
                        FROM {HUB_RATE_TYPE_TABLE}
                        WHERE record_source = '{LIGOVKA_SITE_NAME}'
                    ),
                    new_rate_types AS (
                        INSERT INTO {HUB_RATE_TYPE_TABLE}
                        VALUES 
                            (MD5('buy')::CHAR(32), 'buy', NOW(), '{LIGOVKA_SITE_NAME}'),
                            (MD5('sell')::CHAR(32), 'sell', NOW(), '{LIGOVKA_SITE_NAME}')
                        ON CONFLICT (rate_type_hk) DO NOTHING
                        RETURNING rate_type_hk, rate_type_id
                    ),
                    all_rate_types AS (
                        SELECT * FROM new_rate_types
                        UNION ALL
                        SELECT * FROM existing_rate_types
                    ),
                    new_links_data AS (
                        INSERT INTO {LINK_EXCHANGE_RATE_TABLE} (
                            link_hk,
                            currency_pair_hk,
                            rate_type_hk,
                            load_date,
                            record_source
                        )
                        SELECT DISTINCT
                            MD5(nd.currency_code || '{LIGOVKA_SITE_NAME}' || rt.rate_type_id)::CHAR(32),
                            cp.currency_pair_hk,
                            rt.rate_type_hk,
                            NOW(),
                            '{LIGOVKA_SITE_NAME}'
                        FROM new_data nd
                        JOIN all_currency_pairs cp ON cp.currency_pair_id = nd.currency_code
                        cross JOIN all_rate_types rt
                        ON CONFLICT (link_hk) DO NOTHING
                        RETURNING link_hk, rate_type_hk
                    ),
                    old_links_data AS (
                        select
                            link_hk,
                            rate_type_hk
                        from data_vault.link_exchange_rate
                        where record_source = '{LIGOVKA_SITE_NAME}'
                    ),
                    all_links_data AS (
                        SELECT * FROM new_links_data
                        UNION ALL
                        SELECT * FROM old_links_data
                    )
                    INSERT INTO {SAT_EXCHANGE_RATE_VALUE_TABLE} (
                        exchange_rate_hk,
                        link_hk,
                        rate_value,
                        rate_date,
                        rate_timestamp,
                        load_date,
                        record_source
                    )
                    SELECT 
                        MD5(nd.currency_code || rt.rate_type_id || nd.timestamp)::CHAR(32),
                        ld.link_hk,
                        CASE 
                            WHEN rt.rate_type_id = 'buy' THEN nd.purchase_rate
                            WHEN rt.rate_type_id = 'sell' THEN nd.sale_rate
                        END,
                        nd.timestamp::date,
                        nd.timestamp,
                        NOW(),
                        '{LIGOVKA_SITE_NAME}'
                    FROM new_data nd
                    cross JOIN all_links_data ld
                    JOIN all_rate_types rt ON ld.rate_type_hk = rt.rate_type_hk;
                '''
