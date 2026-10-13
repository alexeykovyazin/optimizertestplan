"""A4-восстановление CEB-IMDb из официальных шаблонов learnedsystems/CEB.

Контекст S0: оригинальные pickle'ы CEB-IMDb (13.6K full / ~3K unique-plans)
недоступны — все ссылки Dropbox в репо мертвы (404, проверено 2026-10-11:
imdb.tar.gz, imdb-unique-plans.tar.gz, imdb-sqls.tar.gz). По правилу плана
§3.1.1 («восстановить по описанию шаблонов либо исключить») восстанавливаем
запросы штатным генератором репо (query_gen/) из выложенных toml-шаблонов.
В репо из IMDb-шаблонов CEB выложены 8 групп: 3b, 7a, 8a, 9a, 9b, 10a, 11a,
11b (самые сложные, 4–16 таблиц) — это НЕ полный CEB-IMDb и не побайтовая
копия опубликованных запросов: параметры сэмплируются заново с фиксированным
сидом, истина по подпланам оригинала недоступна. Корпус помечается как
ceb-imdb-regen; валидация — по PG-эталону как у всех сюит.

Сэмплирование значений и ILIKE-префиксы — по квантилям данных через PG-эталон
(dellg15 imdb, дешёвые одно-колоночные запросы). Тяжёлая верификация EXPLAIN
официального генератора НЕ запускается: нулевые результаты для нашего корпуса
легальны (сравнение всё равно через PG-эталон), и мы не конкурируем за CPU
с S6-прогоном scale.

Запуск:
  python bench/harness/gen_ceb_imdb.py --n-per-template 100
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CEB = os.path.join(ROOT, "third_party", "CEB-repo")
TPL = os.path.join(CEB, "templates")
WORK = os.path.join(ROOT, "third_party", "CEB-gen-work")  # cwd для кэшей
OUT_JSON = os.path.join(ROOT, "third_party", "CEB", "ceb-imdb-regen.json")

PG_HOST = os.environ.get("BENCH_PG_HOST", "dellg15.local")
PG_PORT = os.environ.get("BENCH_PG_PORT", "5432")
PG_USER = os.environ.get("BENCH_PG_USER", "postgres")
PG_PWD = os.environ["BENCH_PG_PWD"]  # пароль только через окружение
PG_DB = os.environ.get("BENCH_PG_DB", "imdb")

TEMPLATES = ["3b", "7a", "8a", "9a", "9b", "10a", "11a", "11b"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-template", type=int, default=100)
    ap.add_argument("--seed", type=int, default=2112)
    ap.add_argument("--templates", default=",".join(TEMPLATES))
    a = ap.parse_args()

    os.makedirs(WORK, exist_ok=True)
    os.chdir(WORK)
    sys.path.insert(0, CEB)

    import pdb
    pdb.set_trace = lambda: None      # заглушки отладчика в генераторе

    import nltk
    for res in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{res}")
        except LookupError:
            nltk.download(res, quiet=True)

    import toml
    import query_gen.query_generator as qgmod
    # в генераторе word_tokenize используется без импорта (строка import
    # закомментирована авторами) — вводим сами
    from nltk.tokenize import word_tokenize
    qgmod.word_tokenize = word_tokenize
    import numpy as np
    qgmod.np = np          # np.percentile в sampling-пути без импорта
    QueryGenerator = qgmod.QueryGenerator

    # lucene-cache/tries генератора — в WORK
    import query_representation.utils as qru
    qru.sql_cache = None   # авторы убрали кэш, оставив ветку с несуществующим
                           # глобалом sql_cache — defining global, ветка
                           # пропускается

    all_out = {}
    for idx, tpl in enumerate(a.templates.split(",")):
        tdir = os.path.join(TPL, tpl)
        fns = [f for f in os.listdir(tdir) if f.endswith(".toml")]
        assert len(fns) == 1, f"{tpl}: ожидался один toml, есть {fns}"
        template = toml.load(os.path.join(tdir, fns[0]))
        random.seed(a.seed + idx)
        qg = QueryGenerator(template, PG_USER, PG_HOST, PG_PORT, PG_PWD, PG_DB)
        print(f"[{tpl}] generating {a.n_per_template}...", flush=True)
        sqls = qg.gen_queries(a.n_per_template)
        # дедуп, сведение однострочника, портирование не делаем здесь
        seen, uniq = set(), []
        for s in sqls:
            one = " ".join(s.split()).rstrip(";").strip()
            if one in seen:
                continue
            seen.add(one)
            uniq.append(one)
        all_out[tpl] = uniq
        print(f"[{tpl}] {len(uniq)} уникальных SQL", flush=True)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(all_out, f, ensure_ascii=False, indent=1)
    total = sum(len(v) for v in all_out.values())
    print(f"TOTAL: {total} queries -> {OUT_JSON}")


if __name__ == "__main__":
    main()
