# Тесты ревью 15.11.2026

Сборки (Windows x64, embedded isql):
- **b69da49179** — HEAD v5.0-impr-opt 15.11, где найдены ошибки (`out_new_*`);
- **06041718cc** — HEAD 12.11, прошлое ревью (`out_prev_*`);
- **3b26d2c7d1** — ветка исправлений `v5.0-impr-opt-review6` (PR IBSurgeon/hqbird#28): b69da49179 + 23 коммита (`out_fix_*`);
- **776d6400cc** — штатный HQbird 5.0 (`out_base_*`). Расширенной статистики нет:
  ошибки команд `alter database add extended statistics` и `alter database refresh statistics` на base ожидаемы.

Каждый скрипт сам создаёт свою базу (`create database '<алиас>'`). Перед запуском удалите старый файл базы.

## Алиасы (databases.conf)

```
tst10bhj = <dir>/tst10bhj.fdb
{
	ExtendedStatistics = true
	ShowExplainCardinality = true
}
```

Так же — `tst10ci`, `tst10tr`, `tst10w1251`, `tst10oj`, `tst10like`, `tst10desc`, `tst10rev`, `tst10blob`.
Без параметров (конфиг по умолчанию): `tst10bhj_def` — для 43b.

## Тесты

| Файл | Находка | Что проверяет | Время |
|---|---|---|---|
| `43_bhj_lost_rows.sql` | Y1 | Batch Hash Join, a 4.5 млн × h 4.2 млн без индекса, редкий ключ: count и sum против эталона без join | ~20 с |
| `43b_bhj_lost_rows_def.sql` | Y1 | то же, алиас `tst10bhj_def` (конфиг по умолчанию) | ~20 с |
| `44_like_eq_twin_ci.sql` | Y2 | LIKE без масок, коллации UNICODE_CI / UNICODE_CI_AI / ES_ES_CI_AI, без индекса; эталон — `sum(iif(col like ..))`. **Файл в UTF8** | секунды |
| `45_like_eq_twin_translit.sql` | Y3 | `set names win1251`, UTF8-колонка с символом U+4E2D, `s like 'abc'` без индекса | секунды |
| `46_like_nomask_win1251.sql` | Y4 | `set names win1251`, UTF8-колонка, `s like 'Мо0а'` без масок. **Файл в кодировке WIN1251** | секунды |
| `47_oj_conversion_view.sql` | Y5 | LEFT JOIN к view / производной таблице / CTE + WHERE по внутренней стороне; смотреть Fetches | ~5 с |
| `48_like_estimates.sql` | Y6, Y10, Y11, Y13, W16 | оценки LIKE (`rows=`) против реального count; план join для Y6 | ~30 с |
| `49_desc_range_reverse.sql` | Y9, W9, Y12 | убывающий индекс и строгая граница на частом значении; параметр + литерал; обратные STARTING WITH / CONTAINING с пробелами | ~3 с |
| `50_full_join_subq.sql` | Y18 | FULL JOIN с коррелированным подзапросом в ON (NOT IN, IN, EXISTS, скалярный, NL), контроль LEFT / RIGHT; смотреть Fetches и `Sub-query … Full Scan`; эталон R1 | ~50 с new, 2 с base и fix |
| `51_not_in_estimate.sql` | Y19 | оценки NOT IN (`rows=`) против count; план join J1 (`not in`) против J2 (`<> and <>`) | ~5 с |
| `52_like_twin_binary.sql` | Y2 (контроль) | бинарные VARCHAR / CHAR, пробел в конце, колонка WIN1251 с литералом UTF8, UNICODE_CI с индексом и без: результат и планы после исправления двойника | секунды |
| `53_like_escape_win1251.sql` | Y4 (контроль) | `set names win1251`: шаблоны с escape без масок и с масками. **Файл в кодировке WIN1251** | секунды |
| `54_old_stat_storage.sql` | W4 | хранилище STAT$ без 7 колонок профиля BLOB: SELECT, оценки, REFRESH, запись в firebird.log | секунды |
| `55_blob_price_bounds.sql` | цена BLOB | `STAT$BLOB_AVG_PAGES` = 1e300, 1e308: план не должен меняться; IN-список | секунды |
| `56_oj_conversion_simple_te.sql` | Y5 | конверсия LEFT → INNER для простой view, view с WHERE, производной таблицы, CTE, вложенной view; без изменений — view с join, с агрегатом, с вычисляемой колонкой | секунды |
| `57_in_notin_estimates.sql` | Y19 | IN / NOT IN для 1, 2, 10 значений из MCV и не из MCV, число и дата | секунды |
| `58_reverse_blanks.sql` | Y12 | обратные STARTING / CONTAINING с хвостовыми пробелами в литерале; контроль W14 | секунды |
| `59_eq_miss_lencap.sql` | W15 | равенство с промахом мимо MCV: UNICODE_CI_AI, NFC / NFD, CHAR OCTETS; контроль — бинарная коллация | секунды |
| `60_corr_subq_outer_eq.sql` | Y20 | коррелированный подзапрос: равенство по полю внешнего потока и диапазон с границей-подзапросом или полем; смотреть индексы подзапроса и Fetches | ~50 с new, секунды fix и base |

## Как запускать

Из папки тестов, с относительным именем файла (тогда isql не печатает полный путь):

```bash
rm -f <dir>/tst10ci.fdb
isql -q -i 44_like_eq_twin_ci.sql > out_new_44_like_eq_twin_ci.txt 2>&1
```

Для штатного HQbird 5.0 нужен `ICU_DATA` с файлами ICU (иначе коллации UNICODE_CI не работают).

Кодировка файлов: `46_like_nomask_win1251.sql` и его выводы — WIN1251; `44_like_eq_twin_ci.sql` — UTF8;
`53_like_escape_win1251.sql` — WIN1251; остальные — ASCII. Сводка — `RESULTS.md`.
