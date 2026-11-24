"""dump_fb.py <csv> <out.txt> - write legacy + explained plans of every query to a text file, print timings."""
import csv
import sys

csv.field_size_limit(10**9)
src, dst = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, encoding="utf-8", errors="replace")))
with open(dst, "w", encoding="utf-8") as out:
    for r in rows:
        if r["kind"] == "prepare":
            out.write("##### " + r["qid"] + "\n" + r["plan"] + "\n" + r["dplan"] + "\n")
            print(r["qid"], " ".join(r["plan"].split())[:900])
for r in rows:
    if r["kind"] == "measured":
        print(r["qid"], r["status"], r["exec_ms"], r["rows"], (r["error"] or "")[:60])
