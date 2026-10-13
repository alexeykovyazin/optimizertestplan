# IMDb (JOB) в Firebird — датасет для теста оптимизатора

Перенос эталонного датасета JOB (Join Order Benchmark) на Firebird 5.0.5
(инстанс 3055) по разделу 4.5 плана. Данные — те же байты, что и в эталонной
БД PostgreSQL на dellg15: CSV выгружены из него командой `COPY ... FORMAT csv`
(каталог `db/imdb/csv/`, 21 файл, ~3.7 ГБ, выгрузка 2026-10-08).

## Состав

| объект | путь |
|---|---|
| генератор DDL | `gen_ddl.py` → `generated/ddl_*.sql`, `column_types.json` |
| сборщик БД | `build_imdb.py` (stages: create/load/constraints/indexes/verify/finalize) |
| голден-копия | `db/golden/imdb_fb5.fdb` (read-only, SHA-256 в `db/imdb/imdb_build_manifest.json`) |
| gbak-архив | `db/archives/imdb_fb5.fbk` |
| запросы (FB-диалект) | `bench/queries/job/*.sql`, оригиналы PG — там же в `original/` |
| манифест корпуса | `bench/manifest/job.yaml` |
| PG-эталон результатов/планов | `results/job_pg_reference/` |
| валидация FB↔PG | `results/job_validation/` |

## Схема

21 таблица IMDb, 108 столбцов, ~70 млн строк (cast_info 36 244 344).
Типы: INTEGER / VARCHAR (по фактическим максимумам textlen) / BLOB SUB_TYPE TEXT
для `movie_info.info` (макс 19 793 симв.) и `person_info.info` (макс 55 656
симв.) — они длиннее максимума Firebird VARCHAR UTF8 (8191).

Ограничения и индексы — точно как в эталонном PG (Harvard dump):
PRIMARY KEY (id) на каждой таблице + 23 вторичных B-tree индекса из
`fkindexes.sql` (movie_id/person_id/... на FK-столбцах). Внешних ключей в PG
нет — здесь тоже нет. `SET STATISTICS` выполнен по всем индексам.
PAGE_SIZE 16384, CHARACTER SET UTF8, коллация по умолчанию (UCS_BASIC —
бинарный порядок; совпадает с collate C эталонного PG).

## Портирование запросов (port_job.py)

Диалект PG в JOB минимальный; правила:
- `role` → `"role"` (зарезервированное слово FB);
- `MIN(<a>.info)` по BLOB-колонкам → `MIN(SUBSTRING(<a>.info FROM 1 FOR 8000))`
  (FB не умеет MIN по BLOB; усечение касается только выводимого значения —
  при сверке с PG допускается префиксное совпадение, `match_truncated`);
- остальное (запятые-соединения, LIKE/IN/BETWEEN, `<>`, диапазоны по строкам)
  идентично в обоих диалектах; сравнение строк в PG — collate C (бинарное),
  в FB — UCS_BASIC (тоже бинарное), расхождений нет.

## Загрузка

```
python bench/datasets/imdb/gen_ddl.py
python bench/datasets/imdb/build_imdb.py --stage create --force
python bench/datasets/imdb/build_imdb.py --stage load --threads 4
python bench/datasets/imdb/build_imdb.py --stage constraints
python bench/datasets/imdb/build_imdb.py --stage indexes
python bench/datasets/imdb/build_imdb.py --stage verify
python bench/datasets/imdb/build_imdb.py --stage finalize   # gbak + golden + sha256
```

Загрузка идёт пачками `EXECUTE BLOCK` по 200 строк (лимит FB: 256 контекстов
на блок; обычный `INSERT ... VALUES (...),(...)` в FB не поддерживается).
Скорость ~15 тыс. строк/с на поток. Пустое поле CSV = NULL: пустых строк ''
в данных PG нет (проверено textlen по всем текстовым колонкам).

## Прогон и валидация

```
# эталон PG (результаты + планы EXPLAIN ANALYZE) — на dellg15:
python bench/harness/job_pg_reference.py gen     # скрипты q_/pe_ + jobref_run.cmd
python bench/harness/job_pg_reference.py run     # scp + прогон на dellg15
python bench/harness/job_pg_reference.py parse   # -> results/job_pg_reference/

# исполнение на FB и сверка:
python bench/harness/job_validate.py --fdb db/imdb/work/imdb_work.fdb
```

Статусы валидации: `match`, `match_truncated` (корректно, см. выше),
`mismatch`, `error`, `prepare_timeout`, `exec_timeout`, `no_pg_reference`.
