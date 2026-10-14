"""Жнец зависших FB-приложений: убирает зомби-вычисления после таймаутов.

Проблема (S8 scale, 2026-10-13/14): клиентский сторож бросает соединение
через timeout_s+45 c, но серверный statement timeout НЕ прерывает тяжёлые
запросы (отмена только в контрольных точках — Hash/Sort секции длинных
COUNT проходят часы). Брошенные соединения продолжают считать на сервере
по ядру на зомби — замеры следующих запросов отравлены.

Решение: цикл каждые 15 c убивает приложения, у которых есть АКТИВНЫЙ
стэйтмент старше AGE_S (по умолчанию 350 c > клиентских 345 c, поэтому
легитимные замеры не задеваются — их стэйтменты живут <345 c):
    DELETE FROM MON$ATTACHMENTS (FB3+)

Запуск на время исполнения сюит:
  python bench/harness/attachment_reaper.py --db E:/fbdata/work/imdb_work_suite.fdb \
      [--hostport 192.168.1.57:3055] [--age-s 350] [--every 15]
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import fbenv  # noqa: E402

FIND_SQL = (
    "SELECT DISTINCT a.mon$attachment_id "
    "FROM mon$attachments a "
    "JOIN mon$statements s ON s.mon$attachment_id = a.mon$attachment_id "
    "WHERE s.mon$state = 1 "
    "AND DATEDIFF(SECOND FROM s.mon$timestamp TO CURRENT_TIMESTAMP) > {age}")
KILL_SQL = "DELETE FROM MON$ATTACHMENTS WHERE MON$ATTACHMENT_ID = {att}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--hostport", default=os.environ.get("FB_HOSTPORT"))
    ap.add_argument("--age-s", type=int, default=350)
    ap.add_argument("--every", type=int, default=15)
    a = ap.parse_args()

    if a.hostport:
        fbenv.HOST_PORT = a.hostport
    killed_total = 0
    while True:
        try:
            db = fbenv.connect_fb(a.db)
            try:
                cur = db.cursor()
                cur.execute(FIND_SQL.format(age=a.age_s))
                ids = [r[0] for r in cur.fetchall()]
                for att in ids:
                    cur.execute(KILL_SQL.format(att=att))
                    killed_total += 1
                    print(f"{time.strftime('%H:%M:%S')} killed attachment "
                          f"{att} (active stmt > {a.age_s}s), "
                          f"total {killed_total}", flush=True)
                cur.close()
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001 - монитор переживает всё
            print(f"{time.strftime('%H:%M:%S')} reaper error: "
                  f"{type(e).__name__}: {str(e)[:120]}", flush=True)
        time.sleep(a.every)


if __name__ == "__main__":
    main()
