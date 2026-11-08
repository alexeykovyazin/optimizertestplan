# Результаты тестов 31–34 (08.11.2026, embedded, ExtendedStatistics=true)

Две сборки: **new** — a3cfa97218 (HEAD 08.11), **old** — f2888abf7c (HEAD 06.11).
Полный вывод: `out_new_<тест>.txt` и `out_old_<тест>.txt`.

## Результаты запросов

| Тест | Запрос | Верно | new | old |
|---|---|---|---|---|
| 31 A1 | `oa left join ob on oa.x = ob.x join oc on oc.k = oa.x` | 20 000 / 20 000 | **`no current record for fetch operation`** | 20 000 / 20 000 |
| 31 A2 | то же + `and ob.y > oa.z` | 20 000 / 9 000 | **400 000 000 / 20 000** | 20 000 / 9 000 |
| 31 A3 | `oc join oa … left join ob …` | 20 000 / 20 000 | 20 000 / 20 000 | 20 000 / 20 000 |
| 31 B1 | `5 > all (select oa.z from oa left join ob …)` | 0 | **1** | 0 |
| 31 B2 | `not (5 > all (…))` | 1 | 1 | 1 |
| 31 B3 | `15 > all (…)` | 1 | 1 | 1 |
| 31 B4 | `5 = any (…)` | 0 | **1** | 0 |
| 32 | PREPARE `nm like '%_%'` | план | **сервер остановлен**, isql rc=3 | план, rc=0 |
| 33 C1 | `rc join rb … where rc.x < 600001 order by rc.x` | 36 000 000 / 600 000 | **48 000 000 / 800 000** | 36 000 000 / 600 000 |
| 33 C2 | то же без ORDER BY | 36 000 000 / 600 000 | 36 000 000 / 600 000 | 36 000 000 / 600 000 |

## Оценки

| Тест | Запрос | Реально | new | old |
|---|---|---|---|---|
| 34 D1 | `pf join pd on pf.k = pd.k` | 1 000 | **1.00** | 1 000 |
| 34 D2 | `pf2 join pd2 on pf2.k = pd2.k` | 500 500 | 500 000 | 500 500 |

## Планы, где видна ошибка (new)

- **31 A1/A2:** `Nested Loop Join (inner) (rows=428169899.80) → Hash Join (outer) …, Table "OC" Full Scan` —
  условие `oc.k = oa.x` ушло в HJ, у OC нет фильтра. Old: `Hash Join (inner)` по `oc.k = oa.x`
  над `Nested Loop Join (outer)`.
- **31 B:** `PLAN HASH (OA NATURAL, OB NATURAL)` без Filter для ANY/ALL. Old: `PLAN JOIN (OA NATURAL, OB NATURAL)`.
- **33 C1:** `Sort → Filter → Hash Join (inner) → RB Full Scan, Record Buffer → RC Full Scan (rows=800000)` —
  нет `RC_X Range Scan` и Filter у RC. C2: `Filter → RC Access By ID → Index "RC_X" Range Scan`.
  Old C1: `Batch Hash Join (batches: 8)` с `Index "RC_X" Range Scan`.
- **34 D1:** `Hash Join (inner) (rows=1.00)`.
