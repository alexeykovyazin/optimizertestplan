# Harness — обвязка тестов оптимизатора (раздел 5 плана)

Python 3.13 + firebird-driver 2.x + DuckDB (истина) + pyarrow (Parquet).
Базовый инстанс: Firebird 5.0.5.1879 HQbird, `localhost:3055`, SYSDBA.

## Модули

| Модуль | Роль (по плану) |
|---|---|
| `fbenv.py` | соединения, счётчики isc_info (page fetches + постатоличные record reads), побайтовые копии, gbak/gfix/isql, prepare-сторож |
| `normalize.py` | нормализация планов + хеши (консервативная, раздел 5) |
| `collector.py` | prepare + план, запросы не исполняются; время подготовки |
| `runner.py` | исполнение: прогрев, повторы (адаптивные), медиана, счётчики, строки, checksum, statement timeout |
| `truth_ceb.py` | истинные кардинальности через DuckDB (4.6); истина считается один раз |
| `pipeline.py` | ключ эталона (4.2), каталоги результатов, побайтовые копии золотого файла |
| `calibrate.py` | разметка fast/heavy + отбор контрольного набора (8.1) |
| `compare.py` | сравнение с эталоном, классы запросов, гейт PASS/WARN/FAIL/INCOMPLETE (9) |
| `ratchet.py` | храповик: план/счётчики (принцип 5, 8.1) |
| `report.py` | Markdown-отчёт + машиночитаемый статус CI |
| `port_ceb.py` | портирование корпуса STATS-CEB (4.5) + манифесты (4.4) |

## Типовые операции

```bash
# 1. Пересоздать золотые копии (после этого снять эталоны заново!)
python bench/datasets/stats/load/build_golden.py

# 2. Пересчитать истину (DuckDB; подпланы с бюджетом 30 с/запрос)
python bench/harness/truth_ceb.py

# 3. Эталонный прогон (collector по всему корпусу + runner + калибровка)
python bench/harness/phase0_make_baseline.py --config pk_fk
#   конфигурация pk (измерение index_config, §7) — отдельный ключ эталона:
python bench/harness/phase0_make_baseline.py --config pk --label baseline_pk

# 4. A/A-прогон: та же сборка на свежей копии; пороги шума
python bench/harness/phase0_aa_noise.py <run_A_dir>            # run B создаётся сам
python bench/harness/phase0_aa_noise.py <run_A_dir> <run_B_dir> [--control-only]

# 5. Сравнение кандидата с эталоном + гейт
#    (см. phase0_compare_demo.py — шаблон для контура)

# 6. Итоговый отчёт фазы 0
python bench/harness/phase0_report.py <run_A_dir> <aa_run_dir>
```

## Ночной контур (элементы, исполняемые на этом инстансе)

```bash
# полное исполнение тяжёлых, цензурированных в baseline (кап 600 с),
# с мержем в эталон того же ключа (бэкап executed.parquet.bak-pre-heavy)
python bench/harness/night_heavy_completion.py <baseline_key_id> --timeout-s 600

# досчёт недостающих истинных кардиналист подпланов (мерж в parquet)
python bench/harness/night_truth_complete.py --budget-s 60
```

## Коды выхода быстрого контура (CI-гейт, принцип 7)

`fast_contour.py` завершается с кодом: 0 = PASS/WARN, 1 = INCOMPLETE,
2 = FAIL. Машиночитаемый статус — `ci_status.json` в каталоге прогона.
Храповик проверяется дважды дёшево: по исполненным запросам (план +
счётчики) и по планам всего корпуса из этапа 1 компиляции (без дублей).

## Ключ эталона (4.2)

`(build_id, SHA-256 файла БД, ODS, хеш конфигурации, index_config)` —
собирается в `pipeline.baseline_key()`. Конфигурация — снапшоты
`bench/config/*.snapshot` + `optimizer_matrix.yaml`. Прогоны — только на
побайтовых копиях золотого файла; изменение любого компонента ключа =
новый эталон, старый для счётчиков не используется.

## Ограничения среды (честно, принцип 7)

- FB 5: нет `RDB$SQL.EXPLAIN` (CARDINALITY) → оценок по узлам, q-error, CERT, P-Error нет.
- `SET OPTIMIZE` через DSQL не работает; в конфиге инстанса
  `OptimizeForFirstRows=true` (не дефолт) — зафиксировано хешем.
- Профайлер PLG$PROF* отключён в конфиге общего инстанса → сверка
  RECORD_SOURCE_ID (4.7) отложена; `detailed_plan` драйвера == выводу
  `isql SET EXPLAIN` (проверено), источник дерева един.
