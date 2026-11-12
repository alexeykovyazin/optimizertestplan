# Тесты ревью 12.11.2026

Сборки (Windows x64, embedded isql):
- **06041718cc** — HEAD v5.0-impr-opt 12.11, где найдены ошибки (`out_new_*`);
- **a3cfa97218** — HEAD 08.11, для сравнения (`out_prev_*`);
- **776d6400cc** — штатный HQbird 5.0, только для теста 37 (`out_base_*`).

Каждый скрипт сам создаёт свою базу (`create database '<алиас>'`). Перед запуском удалите старый файл базы.

## Алиасы (databases.conf)

```
tst9oj = <dir>/tst9oj.fdb
{
	ExtendedStatistics = true
	ShowExplainCardinality = true
}
```

Так же — `tst9bhj`, `tst9esc`, `tst9mig`, `tst9w1251`, `tst9pf`, `tst9rg`. Для W1 и W2 параметры
не нужны: ошибки есть и на конфиге по умолчанию. Старые тесты 00–34 — в папках `tests/` ревью
05.11, 06.11 и 08.11.

## Новые тесты

| Файл | Находка | Что проверяет | Время |
|---|---|---|---|
| `35_oj_on_subq.sql` | W1 | LEFT/RIGHT JOIN, в ON — подзапрос, EXISTS, ANY или ссылка на внешний запрос; эталон — NL по PLAN | секунды |
| `36_bhj_slot_crash.sql` | W2 | BHJ, хэшируемая сторона — производная таблица с записью > 64 КБ. **Останавливает сервер** | секунды |
| `37_like_escape.sql` | W3 | `LIKE 'a\%' ESCAPE '\'` и похожие шаблоны с escape | секунды |
| `38a_stat_prev_create.sql` | W4 | создаёт хранилище STAT$ — **запускать на a3cfa97218** | секунды |
| `38b_stat_new_open.sql` | W4 | открывает ту же базу — **запускать на 06041718cc** | секунды |
| `39_like_win1251.sql` | W6 | клиент WIN1251, UTF8-колонка, `LIKE 'Мо%а'`. **Файл в кодировке WIN1251** | секунды |
| `40_pairfiltered.sql` | W7 | `a join b join e`, два коррелированных фильтра у b | ~10 с |
| `41_range_param_desc.sql` | W8, W9 | убывающий индекс; параметр первым в группе диапазонов | ~20 с |

```bash
isql -q -i 35_oj_on_subq.sql > out_new_35_oj_on_subq.txt 2>&1
```

Для 38: один файл базы `tst9mig` в обоих корнях (один и тот же путь в databases.conf).
Сводка — `RESULTS.md`.
