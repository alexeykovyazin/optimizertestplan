# Корпус оценки оптимизатора Firebird

Реализация плана `firebird-optimizer-testing-plan_1.md` (v2.1, статусы —
Приложение B) на инстансе замеров **Firebird 5.0.5.1879 HQbird, dellg15:3055**
(SYSDBA/masterkey); эталонный PostgreSQL 17.5 (collate C) — там же.

Подробности: `bench/harness/README.md` (обвязка), `bench/datasets/stats/README.md`
(датасет), `bench/config/optimizer_matrix.yaml` (измерения конфигурации),
`porting-plan-remaining-suites.md` §8 (журнал портирования P1–P2 со всеми ловушками).

## Корпус: статус сюит (19.10.2026)

Каждая сюита проходит конвейер **S0–S8**: источник → DDL → загрузка → индексы →
golden (побайтовый read-only FDB с SHA-256) → порт под Firebird + prepare-тест →
PG-эталон → валидация (гейт: **0 mismatch, 0 error**) → бейслайн на FB 5.0.5
(dellg15:3055, 2 повтора, таймаут 300 с).

### Сделано — 12 сюит, ≈ 9,7 тыс. запросов

| Сюита | БД (данные) | Запросов | Валидация S7 | Бейслайн S8 (ключ) | Примечание |
|---|---|---|---|---|---|
| **job** | IMDb (снимок JOB, 74,2 млн строк) | 113 | ✅ 0 mismatch | ✅ `8d618622f064` | 5–17 таблиц, соединения не только по PK/FK |
| **job-complex** | IMDb | 30 | ✅ 0 mismatch | ✅ `8d618622f064` | + набор ~6000 готовых планов статьи как источник порядков соединения |
| **job-light** | IMDb | 70 | ✅ 0 mismatch | ✅ `8e23f5f87eea` | звёздные PK-FK соединения, числовые предикаты |
| **scale** | IMDb | 500 | ✅ 0 mismatch | ✅ `8e23f5f87eea` | изоляция ошибок оценки по масштабу шаблонов |
| **synthetic** | IMDb | 5000 | ✅ 0 mismatch | 🟡 collected (тот же ключ) | исполнение — в ночном контуре |
| **tpch** | TPC-H SF1 (dbgen 2.17.2) | 22 | ✅ 0 mismatch | ✅ `c4adffec0450` | подзапросы, декорреляция (Q2, Q4, Q17, Q20–Q22) |
| **stats-ceb** | STATS (Stack Exchange, 8 таблиц) | 146 + 632 single + 2603 subplans | ✅ 0 mismatch | ✅ `8d618622f064` | A/B-контроль 778/778; истина подпланов готовая |
| **ceb-imdb-regen** | IMDb | 121 | ✅ 0 mismatch | ✅ `8e23f5f87eea` | regen-версия CEB; оригинальные пиклы недоступны (Dropbox мёртв) |
| **jcch-norm / jcch-skew** | TPC-H схема, коррелированные+перекошенные данные (dbgen -k; lineitem ровно 6 000 000) | 22 + 22 | ✅ 0 mismatch | ✅ `1bb2761caa0a` | медиана 2,7 с (norm) / 4,3 с (skew); та же форма запроса на разных данных |
| **dsb-s1 / dsb-s2** | TPC-DS схема SF1 с корреляциями DSB (25 таблиц, реальные NULL) | 230 + 235 | ✅ 0 mismatch | ✅ `185688298633` | медиана 1,74 с (s1) / 1,87 с (s2); 60/505 исключено — INTERSECT/ROLLUP/GROUPING нет в FB5 (`bench/manifest/dsb-*-excluded.yaml`) |

Все 12 сюит имеют PG-эталон (DSB — 100 % покрытие, 465/465), prepare-тесты
и отчёты валидации в `results/*_validation/`. Вариант эталона фазы 0
с конфигурацией `pk` — `e5455d2547a4`.

### Не сделано

| Набор | Приоритет | БД (план) | Что даёт | Статус |
|---|---|---|---|---|
| **SQLStorm** | P3 | StackOverflow 1/12/220 ГБ | Широта SQL (18K+ LLM-запросов), top-N, выбросы | ❌ не начат |
| **Hollywood** | P3 | синтетика по IMDb SF10/SF100 | Поведение на масштабе | ❌ не начат |
| **CERT-оракул** | P2 | — (без исполнения) | Нарушения монотонности оценок | ❌ не начат, разблокирован бейслайнами |
| **TAQO** | P3 | текущий корпус | Зазор до оптимума (`PLAN JOIN`/`PLAN HASH`) | ❌ не начат, разблокирован бейслайнами |
| **Stack Parametric** (Kepler) | P4 | StackExchange | Чувствительность плана к параметрам | ❌ не начат |
| **CH-benCHmark** | P4 | TPC-C | Дрейф данных, устаревшая статистика | ❌ не начат |
| **LDBC SNB BI** | P4 | Social Network | Путевые и циклические шаблоны | ❌ не начат |
| **CardBench** | P4 | 20 реальных БД | Однотабличная селективность | ❌ не начат |
| SF10-масштаб TPC-H / JCC-H / DSB | P2–P3 | те же схемы ×10 | Масштабирование | ❌ не начат |
| CEB-IMDb full (13,6K) | — | IMDb | — | ⛔ закрыт: оригинальные пиклы недоступны |

## Быстрый старт

```bash
pip install firebird-driver duckdb pyarrow pyyaml

# золотые копии pk / pk_fk + gbak + read-only + SHA-256
python bench/datasets/stats/load/build_golden.py

# истина (DuckDB): корни + одно-табличные полностью, подпланы с бюджетом
python bench/harness/truth_ceb.py

# эталонный прогон (collector по 3381 запросам + runner 146+632+выборка)
python bench/harness/phase0_make_baseline.py --config pk_fk

# A/A-шум (та же сборка дважды) — пороги для гейта
python bench/harness/phase0_aa_noise.py <run_A_dir> [--control-only]

# быстрый контур (8.1): компиляция -> изменённые планы -> контрольный набор -> гейт
# коды выхода: 0 = PASS/WARN, 1 = INCOMPLETE, 2 = FAIL
python bench/harness/fast_contour.py <baseline_key_id>
python bench/harness/fast_contour.py <baseline_key_id> --mutate-plans   # симуляция кандидата

# ночное (исполняемое на этом инстансе): тяжёлые целиком + досчёт истины
python bench/harness/night_heavy_completion.py <baseline_key_id> --timeout-s 600
python bench/harness/night_truth_complete.py --budget-s 60

# самопроверка гейта на синтетических мутациях (все классы сравнения)
python bench/harness/phase0_compare_demo.py <run_A_dir>

# итоговый отчёт фазы 0
python bench/harness/phase0_report.py <run_A_dir> <aa_run_dir>
```

Переменные окружения: `FB_HOSTPORT` — целевой инстанс FB (по умолчанию
локальный 3055); `BENCH_PG_DSN` / `BENCH_PG_PWD` — эталонный PostgreSQL
для валидации S6/S7 (пароль в репозитории не хранится); `DELLG15_SSH` —
ssh-алиас машины замеров.

## Что реализовано

- Обвязка: collector (prepare+план, без исполнения), runner (прогрев, медиана,
  счётчики isc_info, statement timeout, checksum), истина (DuckDB), compare
  (классы запросов + гейт PASS/WARN/FAIL/INCOMPLETE, §9), храповик, отчёт.
- Нормализация планов: консервативная, `detailed_plan` драйвера == выводу
  `isql SET EXPLAIN` (проверено).
- Золотые копии по 4.2: побайтовые копии, read-only, ключ эталона
  (сборка, SHA-256 файла БД, ODS, хеш конфигурации, index_config).
- Корпус фазы 0 (STATS-CEB, P1): 146 корневых + 632 одно-табличных + 2603
  подплановых запроса, портированы по правилам 4.5, манифесты 4.4, теги,
  истина 4.6; трёхсторонний A/B (hqbird + impropt, 778/778).
- Порт P2 (см. таблицу выше): TPC-H, JOB-семейство, CEB-regen, JCC-H
  (собственный фикс 64-битной арифметики dbgen под Windows), DSB (msbuild
  тулсета, генерация 505 запросов), все — через S6 PG-эталон и S7-валидацию.
- Калибровка: fast/heavy по эталонному времени, контрольный набор (жадное
  покрытие тегов ≥2), вынесено в `results/calibration` (4.3).

## Осознанные ограничения (принцип 7 — нет ложного PASS)

1. FB 5: нет `RDB$SQL.EXPLAIN` (CARDINALITY) → q-error, CERT, P-Error недоступны.
2. `OptimizeForFirstRows=true` в конфиге инстанса замеров (не дефолт) —
   зафиксировано снапшотом и хешем; `SET OPTIMIZE` через DSQL не работает.
3. Профайлер PLG$PROF* отключён в конфиге инстанса → проверка RECORD_SOURCE_ID
   (4.7) отложена до выделенного инстанса.
4. Тяжёлые/ночные цели корпусa (synthetic исполнение, SF10-масштабы) — в
   ночном контуре; быстрый/ночной контуры как автоматический сервис ещё
   не собраны (§8 плана).
