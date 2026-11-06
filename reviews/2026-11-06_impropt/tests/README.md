# Тесты ревью 06.11.2026

Сборка `f2888abf7c` (Windows x64, embedded isql). Подготовка и алиасы — как в
`../../2026-11-05_impropt/tests/README.md` (`tst2`, `tst2def`, `tstnone`, `tstbhj`, `tstbhjlow`).

## Порядок

1. Тесты 00–24 ревью 05.11 (папка `../../2026-11-05_impropt/tests/`) — без изменений.
   Вывод на `f2888abf7c`: `out_00_20.txt` и начало `out_22_29.txt`.
2. Новые тесты этой папки — на `tst2` после `17_m2.sql` (нужны таблицы `t` и `tz`):

| Файл | Что проверяет |
|---|---|
| `25_new.sql` | R4 и R1 с индексом, пары диапазонов одного направления, три границы, пустой диапазон, поле справа, обратные STARTING/CONTAINING/LIKE по колонке NONE |
| `26_eqjoin.sql` | U1: join двух колонок с MCV, у второй MCV вне первой |
| `27_reverse.sql` | U3, U4: обратные `'lit' CONTAINING col` и `'lit' STARTING WITH col` по UTF8, UNICODE_CI, CHAR |
| `28_unique.sql` | U5: уникальная DOUBLE с диапазоном значений меньше 1; R1 для уникального текста |

```bash
TMO=600 ./run.sh 25_new.sql 26_eqjoin.sql 27_reverse.sql 28_unique.sql
```

Результаты — `RESULTS.md`.
