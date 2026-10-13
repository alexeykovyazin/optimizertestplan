# Корпус оценки оптимизатора Firebird — фаза 0 (реализация)

Реализация разделов 0–1 плана `firebird-optimizer-testing-plan_1.md` на базовом
инстансе **Firebird 5.0.5.1879 HQbird, localhost:3055** (SYSDBA/masterkey).

Подробности: `bench/harness/README.md` (обвязка), `bench/datasets/stats/README.md`
(датасет), `bench/config/optimizer_matrix.yaml` (измерения конфигурации).

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

## Что реализовано (фаза 0)

- Обвязка: collector (prepare+план, без исполнения), runner (прогрев, медиана,
  счётчики isc_info, statement timeout, checksum), истина (DuckDB), compare
  (классы запросов + гейт PASS/WARN/FAIL/INCOMPLETE, §9), храповик, отчёт.
- Нормализация планов: консервативная, `detailed_plan` драйвера == выводу
  `isql SET EXPLAIN` (проверено).
- Золотые копии по 4.2: побайтовые копии, read-only, ключ эталона
  (сборка, SHA-256 файла БД, ODS, хеш конфигурации, index_config).
- Корпус STATS-CEB (P1): 146 корневых + 632 одно-табличных + 2603 подплановых
  запроса, портированы по правилам 4.5, манифесты 4.4, теги, истина 4.6.
- Калибровка: fast/heavy по эталонному времени, контрольный набор (жадное
  покрытие тегов ≥2), вынесено в `results/calibration` (4.3).

## Осознанные ограничения (принцип 7 — нет ложного PASS)

1. FB 5: нет `RDB$SQL.EXPLAIN` (CARDINALITY) → q-error, CERT, P-Error недоступны.
2. `OptimizeForFirstRows=true` в конфиге общего инстанса (не дефолт) —
   зафиксировано снапшотом и хешем; `SET OPTIMIZE` через DSQL не работает.
3. Профайлер PLG$PROF* отключён в конфиге инстанса → проверка RECORD_SOURCE_ID
   (4.7) отложена до выделенного инстанса.
4. JOB/IMDb в этой рабочей копии отсутствует (нужен PostgreSQL-этап загрузки);
   корпус фазы 0 — STATS-CEB.
