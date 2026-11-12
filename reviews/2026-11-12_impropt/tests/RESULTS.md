# Результаты тестов 35–41 (12.11.2026, embedded, ExtendedStatistics=true)

Сборки: **new** — 06041718cc (HEAD 12.11), **prev** — a3cfa97218 (HEAD 08.11), **base** — 776d6400cc
(штатный HQbird 5.0). Полный вывод: `out_new_<тест>.txt`, `out_prev_<тест>.txt`, `out_base_<тест>.txt`.

## Результаты запросов

| Тест | Запрос | Верно | new | prev |
|---|---|---|---|---|
| 35 Q1–Q4, Q6 | `oa left join ob on oa.x = ob.x and <подзапрос / EXISTS / NOT EXISTS / OR EXISTS / > ANY>` — совпадений | 5 400 | **10 000** | 5 400 |
| 35 Q1b | то же + `where ob.id is null` | 4 600 | **0** | 4 600 |
| 35 Q5 | в ON ссылка на поле внешнего запроса | 4 000 | **10 000** | 4 000 |
| 35 I1, RJ1 | индекс на ob.x; RIGHT JOIN | 5 400 | **10 000** | 5 400 |
| 35 Q7, Q8 | контроль: некоррелированный подзапрос; простое неравенство | верно | верно | верно |
| 36 | BHJ над двумя производными таблицами, запись реки ~70 КБ | 225 | **сервер остановлен**, isql rc=3 | 225 |
| 37 | `s like 'a\%' escape '\'` и ещё 3 шаблона | 250 | **0** | **0** (base: 250) |
| 38b | любой SELECT после хранилища от prev | данные | **`Column unknown STAT$BLOB_LEVELS`**, rc=1 | — |
| 39 | `set names win1251; s like 'Мо%а'` | 2 500 | **PREPARE: `Cannot transliterate character between character sets`**, rc=1 | 2 500 |

## Оценки и планы

| Тест | Запрос | Реально | new | prev |
|---|---|---|---|---|
| 40 Q2 | `a join b join e`, два фильтра у b | 2 500 | выход позиции b **0.49** (49), NL в e: **2 498 500 fetches** | HJ: 114 029 fetches |
| 41 A1 / A1b | `x > ? and x > 10` / `x > 10 and x > ?` | — | **99 991** / 49 995.5 | 49 995.5 / 49 995.5 |
| 41 A2 / A2b | `x < ? and x < 100 and x > 50` / другой порядок | — | **51** / 25.5 | 25.5 / 25.5 |
| 41 A3 / A3b | две колонки, параметр первым | — | **99 982** / 24 995.5 | 24 995.5 / 24 995.5 |
| 41 B1d / B6d | `xd > 10`, убывающий индекс; то же в join | 99 990 | **5 000.95**; join (B6d) — NL, 501 759 fetches (asc B6 — HJ, 204 067) | так же |
| 41 B5d / B8d | `xd > 5 and xd < 90000`; то же в join | 89 994 | **251**; join (B8d) — NL, 451 600 fetches (asc B8 — 194 796) | так же |

## Планы, где видна ошибка (new)

- **35:** `Hash Join (outer)` без Filter над OB: конъюнкт с подзапросом не попал ни в условие HJ, ни в фильтр.
  Prev: `Nested Loop Join (outer)` с Filter.
- **36:** `PLAN HASH (JOIN (L A NATURAL, L B INDEX (B_K)), JOIN (D A2 NATURAL, D B2 INDEX (B_K)))`,
  дальше вывода нет; в firebird.log — Access violation.
- **37:** A1–A5, B1, B2 — 0 строк, контроль A6 (`'abc%'` без escape) — 250. Двойник `=` или STARTING WITH
  строится вместе с символом escape (Optimizer.cpp:5474–5479).
- **40 Q2:** `Nested Loop Join (inner) (rows=24.52)` → `Index "E_K" Range Scan` по неселективному ключу;
  Fetches = 2 498 500.
