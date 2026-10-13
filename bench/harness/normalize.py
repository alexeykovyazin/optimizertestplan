"""Нормализация планов перед хешированием (раздел 5 плана).

Сохраняется:
  - порядок и метод соединения (NESTED LOOP / HASH / MERGE / SORT);
  - метод доступа и имя индекса, тип сканирования (Unique/Full/Partial),
    bitmap AND/OR;
  - сортировки, фильтры, агрегации, вид обработки подзапросов.

Удаляется: только случайные пробелы и регистр закавыченных идентификаторов.
Кардиности и стоимость в планах FB5 отсутствуют (они появятся в FB 6 через
RDB$SQL.EXPLAIN) — удалять нечего. Агрессивная нормализация недопустима
(ложный вывод «план не изменился»), поэтому нормализация консервативна.
"""
from __future__ import annotations

import hashlib
import re


def normalize_plan(plan_text: str | None) -> str:
    if not plan_text:
        return ""
    lines = []
    for raw in plan_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        # сворачиваем пробелы, сохраняя маркеры дерева (->, вложенность via порядок строк)
        line = re.sub(r"\s+", " ", line)
        lines.append(line)
    return "\n".join(lines)


def plan_hash(plan_text: str | None) -> str:
    return hashlib.sha1(normalize_plan(plan_text).encode("utf-8")).hexdigest()


def simple_plan_hash(plan_text: str | None) -> str:
    """Для простого плана (PLAN JOIN (...)) — одна строка, регистр не важен."""
    if not plan_text:
        return ""
    t = re.sub(r"\s+", " ", plan_text.strip()).lower()
    return hashlib.sha1(t.encode("utf-8")).hexdigest()


def plan_features(plan_text: str | None) -> dict:
    """Извлечь признаки плана для отчёта/разрезов по тегам."""
    n = normalize_plan(plan_text).upper()
    return {
        "has_hash_join": "HASH JOIN" in n,
        "has_merge": "MERGE" in n,
        "nested_loop_count": n.count("NESTED LOOP"),
        "sort_count": n.count("SORT"),
        "bitmap_count": n.count("BITMAP"),
        "index_scan_count": len(re.findall(r'INDEX "([A-Z$0-9_]+)"', n)),
        "natural_count": n.count("NATURAL"),
    }
