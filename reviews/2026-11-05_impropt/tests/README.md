# Тесты повторного ревью 05.11.2026

isql-скрипты, которыми проверялись находки на сборке `87a3e409cd` (Windows x64, embedded).
Результаты прогона — `RESULTS.md`.

## Подготовка

1. Скопировать `output_x64_release` в папку `fbroot` рядом с папкой тестов
   (`run.sh` ищет `../fbroot/isql.exe`).
2. Добавить алиасы в `fbroot/databases.conf` (`<dir>` — папка тестов):

```
tst2 = <dir>/t2.fdb
{
    ExtendedStatistics = true
    ShowExplainCardinality = true
}
tstnone = <dir>/tn.fdb
{
    ExtendedStatistics = true
}
tst2def = <dir>/t2def.fdb
```

`tst2def` — без параметров, то есть конфиг по умолчанию (`ExtendedStatistics = false`).

## Порядок запуска

- `00_setup.sql` … `17_m2.sql` — по порядку на `tst2`: каждый скрипт использует таблицы
  предыдущих.
- После `17_m2.sql` скопировать `t2.fdb` в `t2def.fdb` (нужен индекс `ob_x`), затем
  `18_m2def.sql` и `19_s8.sql` (оба на `tst2def`).
- `07_none.sql` создаёт `tn.fdb` в кодировке NONE (файл содержит байты Latin-1).
  Перед `20_n1.sql` удалить `tn.fdb`.

```bash
./run.sh 00_setup.sql 01_s1.sql 02_refresh_scan.sql
```

`TMO` — таймаут одного скрипта в секундах (по умолчанию 120).

## Что проверяет каждый скрипт

| Скрипт | Находка |
|---|---|
| 01 | S1 (агрегат без GROUP BY) |
| 02, 03 | S5 (STAT$SCALE, `n = 12.34`) |
| 04 | S2 (колонка без статистики) |
| 05, 10 | S4 (SAMPLE), N2 (ND в SAMPLE) |
| 06 | S7 (ALTER TYPE) |
| 07 | S11 (кодировка NONE) |
| 08, 09 | M1 (hash outer join не выбирается) |
| 11–13, 16 | R1 (открытый конец, 1 бин), R4 (BETWEEN) |
| 14 | E8 (текстовая гистограмма) |
| 15 | R3 (параметры и выражения) |
| 17, 18 | M2 (неверный результат LEFT JOIN) |
| 19 | S8 (ORDER BY над BHJ, не воспроизвелось) |
| 20 | N1 (хранилище без STAT$SCALE) |
