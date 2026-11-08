# Тесты ревью 08.11.2026

Сборки (Windows x64, embedded isql):
- **a3cfa97218** — HEAD v5.0-impr-opt 08.11, где найдены ошибки;
- **f2888abf7c** — HEAD 06.11, для сравнения.

Каждый скрипт сам создаёт свою базу (`create database '<алиас>'`). Перед запуском удалите старый файл базы.

## Алиасы (databases.conf)

```
tst8oj = <dir>/tst8oj.fdb
{
	ExtendedStatistics = true
	ShowExplainCardinality = true
}
```

Так же — `tst8like`, `tst8sort`, `tst8eq`. Пробы из `probes/` используют алиасы `probe1` … `probe8`
с теми же двумя параметрами. Старые тесты 00–28 — `../../2026-11-05_impropt/tests/` и
`../../2026-11-06_impropt/tests/` (алиасы `tst2`, `tst2def`, `tstnone`, `tstbhj`, `tstbhjlow`).

## Новые тесты

| Файл | Находка | Что проверяет | Время |
|---|---|---|---|
| `31_oj_parent.sql` | V1, V2 | LEFT JOIN + INNER JOIN по полю внешней стороны; ANY/ALL над LEFT JOIN | ~1 мин на a3cfa97218, ~5 мин на f2888abf7c (NL) |
| `32_like_crash.sql` | V3 | PREPARE `LIKE '%_%'` по VARCHAR со статистикой длин. **Останавливает сервер** | секунды |
| `33_sort_bhj.sql` | V4 | ORDER BY над join с BHJ и возвратом сортировки | ~1 мин (5 млн строк) |
| `34_eqjoin_min.sql` | V5 | eqjoinsel: все значения одной стороны в MCV, у другой — в хвосте | секунды |

```bash
isql -q -i 31_oj_parent.sql > out_new_31_oj_parent.txt 2>&1
```

Вывод на двух сборках: `out_new_<тест>.txt` (a3cfa97218) и `out_old_<тест>.txt` (f2888abf7c).
Сводка — `RESULTS.md`.

## Пробы (`probes/`)

Короткие скрипты агентов ревью, вывод в `.out`. Группы: `n1_*` — хранилище STAT$ (V6);
`p1_*` — outer join (V1, V2, M2, C7); `p3_*` — eqjoin (U1, V5, E2, E4); `p4_*` — обратный текст
(U3, U4, V11–V13); `p5_*` — диапазоны (R1, U5, U9, V15); `p6_*` — подстроки и длины (E1, V3, V7–V10);
`p7_*` — BHJ (B2, S8, V4); `p8_*` — порядок join (U2, V14, U8, V4). Пробы сделаны только на a3cfa97218.
Большой вывод `p8_rs3.out` (800 КБ строк) не включён — то же показывает `33_sort_bhj.sql`.
