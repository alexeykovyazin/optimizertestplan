# Многоколоночные статистики для JOB и JOB-light: анализ кандидатов

Дата: 27.10.2026. Корпус: **113 запросов JOB** (bench/queries/job) +
**70 запросов job-light** (bench/queries/job-light).
Метод: парсер SQL (`bench/harness/ext_stats_candidates.py`) извлекает из
каждого запроса алиасы, join-рёбра (`a.x = b.y`) и фильтры
(`a.c <op> literal`, LIKE, IN, BETWEEN, IS [NOT] NULL); кандидат —
таблица, которая **в одном запросе** соединяется по одной колонке и
фильтруется по другой (совместный MCV пары даёт оптимизатору
обусловленную селективность — тот же механизм, что у словарей в скрипте
для CEB). Типы колонок сверены со схемой голден-БД (108 колонок, 21
таблица). Полные таблицы по всем парам — REPORT_raw.md, генератор —
ext_stats_candidates.py.

Замер покрытия ключевыми паттернами (регэксп-контроль, согласуется с
парсером): TITLE.production_year — 77 JOB / 56 job-light,
cn.country_code — 61 JOB, n.gender — 27 JOB, mk.keyword_id — 26 JOB,
mc.company_type_id — 10 JOB / 16 job-light, mi.info_type_id — 28
job-light, mi_idx.info_type_id — 26 job-light, ci.role_id — 8 JOB / 15
job-light.

## Два паттерна использования

1. **Словарный** (как в скрипте 26.10 для CEB): маленькая таблица,
   join по ID, фильтр по осмысленной колонке (`it.info = 'trivia'`,
   `rt.role = 'actor'`, `kt.kind = 'movie'`, `cn.country_code = '[us]'`).
2. **Факт-таблица**: join по MOVIE_ID (к TITLE), равенство по типовой
   колонке (`mi.info_type_id = 112`, `mc.company_type_id = 2`,
   `ci.role_id = 1`, `mk.keyword_id = k.id` + фильтр по k.keyword).
   Это **основной паттерн job-light**.

## Уже созданы (скрипт 26.10, STAT$MULTI_COLUMNS)

Шесть словарей CEB закрывают заметную часть JOB:
INFO_TYPE(ID, INFO) — 61 запрос, KIND_TYPE(ID, KIND) — 26,
COMPANY_TYPE(ID, KIND) — 24, COMP_CAST_TYPE(ID, KIND) — 21,
ROLE_TYPE(ID, ROLE) — 19, LINK_TYPE(ID, LINK) — 14.

## Рекомендуемые новые (в порядке приоритета)

### Приоритет 1 — TITLE (главный паттерн JOB и job-light)
| DDL | покрытие | комментарий |
|---|---|---|
| `TITLE(ID, PRODUCTION_YEAR)` | 80 JOB (77 диапазонных) + 56 job-light | join по id + `production_year > 2000`-подобные диапазоны; самый частый паттерн обеих сюит |
| `TITLE(KIND_ID, PRODUCTION_YEAR)` | 22 JOB + 5 job-light | совместная селективность `kind_id = 1 AND production_year > 1990` |
| `TITLE(ID, KIND_ID)` | 7 job-light | join по id + `kind_id = 1` |

### Приоритет 2 — словари вне CEB-шестёрки
| DDL | покрытие | комментарий |
|---|---|---|
| `KEYWORD(ID, KEYWORD)` | 69 JOB | `k.keyword = '...'` / LIKE; MCV помогает равенствам и обусловленной оценке join |
| `COMPANY_NAME(ID, COUNTRY_CODE)` | 64 JOB | `country_code = '[us]'`, `IS NOT NULL` |
| `NAME(ID, GENDER)` | 27 JOB | `n.gender IS NULL / = 'f'` |
| `NAME(ID, NAME_PCODE_CF)` | 3 JOB | опционально (pcode-равенства) |
| `CHAR_NAME(ID, NAME)` | 8 JOB | опционально |

### Приоритет 3 — факт-таблицы (основной паттерн job-light)
Сбор заметно тяжелее (MOVIE_INFO ~14.5M строк) — режим SCAN по
умолчанию; для точности по конкретной структуре можно точечный
`ALTER DATABASE REFRESH STATISTICS <имя> FULL`.
| DDL | покрытие | комментарий |
|---|---|---|
| `MOVIE_INFO(MOVIE_ID, INFO_TYPE_ID)` | 28 job-light (+JOB) | `mi.info_type_id = N` при join по movie_id |
| `MOVIE_INFO_IDX(MOVIE_ID, INFO_TYPE_ID)` | 26 job-light + 21 JOB | там же, включая диапазоны `info >= N` |
| `MOVIE_COMPANIES(MOVIE_ID, COMPANY_TYPE_ID)` | 16 job-light + ~25 JOB | `mc.company_type_id = N` |
| `CAST_INFO(MOVIE_ID, ROLE_ID)` | 15 job-light + 8 JOB | `ci.role_id = N` |
| `MOVIE_KEYWORD(MOVIE_ID, KEYWORD_ID)` | 13 job-light + 26 JOB | join по movie_id, фильтр через keyword-словарь |

### Ниже приоритета (LIKE-фильтры по note/name)
`MOVIE_COMPANIES(MOVIE_ID, NOTE)` (32 JOB), `CAST_INFO(MOVIE_ID, NOTE)`
(30 JOB), `CAST_INFO(PERSON_ID, NOTE)` (27), `NAME(ID, NAME)` (27),
`COMPANY_NAME(COUNTRY_CODE, NAME)` (11) — фильтры почти всегда
`LIKE '%...%'`, для которого MCV-гистограмма селективность не улучшает;
пользуясь только для равенств/IS NOT NULL. Создавать во вторую волну.

## Что совместной статистикой не покрыть
`movie_info.INFO` и `person_info.INFO` — **BLOB**: сборщик расширенной
статистики BLOB-значения не декодирует (и SHOW STATISTICS их не читает),
пар с BLOB-колонкой не создать. Фильтры `mi.info LIKE ...` (49 JOB) /
`pi.info LIKE ...` остаются с обычной оценкой; косвенно их селективность
уже обусловлена словарём `INFO_TYPE(ID, INFO)` (varchar), который
существует.

## Статистика PostgreSQL (dellg15, imdb, 17.5) на те же запросы

Инвентаризация (27.10.2026):
- `default_statistics_target = 100`; **расширенных статистик 0**
  (`pg_statistic_ext` пуст — CREATE STATISTICS никогда не создавались)
- при этом **одноколоночная статистика собрана на ВСЕ колонки всех 21
  таблиц** (518 строк в pg_stats: n_distinct, MCV, гистограмма,
  correlation) — включая TEXT-колонки: `movie_info.info` (в Firebird это
  BLOB, который сборщик ext stats не читает; PG на нём держит 100 MCV +
  гистограмму из 101 ведра)

Что PG знает по колонкам наших кандидатов: role_id, company_type_id,
gender, title.kind_id, mi_idx.info_type_id — целиком через MCV
(малая кардинальность, точные частоты); production_year — MCV 100 +
гистограмма; movie_id/country_code/keyword.keyword/info_type.info —
гистограммы; correlation указан для всех.

**Но все межколоночные связи PG не знает** — замер на точных парах
наших кандидатов (EXPLAIN ANALYZE, оценка/факт):
- `title WHERE kind_id=1 AND production_year>2005`: 66 984 против
  **216 280** — занижение ×3.2
- `title WHERE kind_id=1 AND production_year BETWEEN 1898 AND 2020`:
  163 142 против **653 965** — ×4.0
- `cast_info WHERE role_id=1 AND movie_id>2000000`: 714 099 против
  **3 070 160** — ×4.3
- `movie_info WHERE info_type_id=112 AND info IS NOT NULL`: 6 238 против
  **0** (info_type_id 112 вне MCV movie_info — интерполяция гистограммы
  вместо нуля)

Вывод: PG-эталон считается на тех же **одноколоночных** данных, что и
базовый Firebird; предлагаемые FB-многоколоночные статистики —
потенциальное преимущество над PG-планировщиком на связанных парах
(в PG аналогичный механизм — CREATE STATISTICS (dependencies, ndistinct,
mcv) — на этой БД не создавался). Для честного A/B «FB ext stats vs PG»
стоит держать в голове, что пары kind_id+production_year,
role_id+movie_id PG оценивает так же плохо, как Firebird без ext stats.

## Готовый скрипт (консолидированный)

См. candidates.sql: 14 структур — 3 TITLE + 5 словарей + 5 факт-пар +
1 опциональная; все имена ≤ 31 символа. Порядок выполнения как в скрипте
26.10: ADD EXTENDED STATISTICS уже есть, CREATE по одной DDL в отдельной
транзакции, затем один `ALTER DATABASE REFRESH STATISTICS`.

Оговорка о механике: условная оценка соединений 4.13 берёт **один**
предикат внешнего потока (равенство → IN-список → двусторонний диапазон),
поэтому пары (ID, колонка-фильтр) рекомендуются как отдельные структуры,
а не одна тройка (ID, KIND_ID, PRODUCTION_YEAR).
