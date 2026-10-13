# Датасет `stats` (упрощённый STATS — дамп stats.stackexchange.com)

Источник: [End-to-End CardEst Benchmark (STATS-CEB)](https://github.com/Nathaniel-Han/End-to-End-CardEst-Benchmark),
датасет `datasets/stats_simplified` (упрощённая версия дампа Stats Stack Exchange, 8 таблиц).
Лицензия исходного дампа: CC BY-SA (sha-sums stackexchange); проверить перед публикацией корпуса (раздел 13).

Оригинальные файлы: `third_party/STATS-CEB/datasets/stats_simplified/` (не в gitbench-корпусе,
дублируются сюда только DDL и манифесты).

## Схема и объём (проверено загрузчиком)

| Таблица | Строк | Столбцы |
|---|---|---|
| users | 40 325 | Id, Reputation, CreationDate, Views, UpVotes, DownVotes |
| posts | 91 976 | Id, PostTypeId, CreationDate, Score, ViewCount, OwnerUserId, AnswerCount, CommentCount, FavoriteCount, LastEditorUserId |
| postLinks | 11 102 | Id, CreationDate, PostId, RelatedPostId, LinkTypeId |
| postHistory | 303 187 | Id, PostHistoryTypeId, PostId, CreationDate, UserId |
| comments | 174 305 | Id, PostId, Score, CreationDate, UserId |
| votes | 328 064 | Id, PostId, VoteTypeId, CreationDate, UserId, BountyAmount |
| badges | 79 851 | Id, UserId, "Date" |
| tags | 1 032 | Id, "Count", ExcerptPostId |

Отступления от оригинала (PostgreSQL):
- `SERIAL PRIMARY KEY` → `INTEGER NOT NULL PRIMARY KEY` (счётчик не нужен, id в CSV);
- `Date` и `Count` — зарезервированные слова Firebird → столбцы созданы квотированными
  (`"Date"`, `"Count"`), запросы портированы с теми же кавычками (см. port_notes в манифестах).

## Конфигурации индексов (4.1)

- `pk` — только первичные ключи: `ddl_pk.sql`
- `pk_fk` — pk + вторичные индексы на столбцах соединений: `ddl_pk.sql` + `ddl_pk_fk.sql`

## Золотые копии (4.2)

Строятся `load/build_golden.py`: загрузка CSV → `SET STATISTICS` по всем индексам →
проверка числа строк → gbak-архив (`db/archives/stats_<cfg>.fbk`) → побайтовая копия
`db/golden/stats_<cfg>.fdb` → `gfix -mode read_only` → SHA-256 в `golden_manifest.json`.

Прогоны используют ТОЛЬКО побайтовые копии золотого файла (не gbak-restore):
`pipeline.make_work_copy()` копирует и сверяет SHA-256 до и после.

## Пересоздание

```bash
python bench/datasets/stats/load/build_golden.py
```

После пересоздания все эталоны снимаются заново (ключ эталона включает SHA-256 файла).
