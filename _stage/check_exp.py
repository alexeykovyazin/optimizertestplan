import json, sys
p = r"E:\bench\parscan\expected_job.json"
raw = open(p, "rb").read()
print("bytes:", len(raw))
d = json.loads(raw.decode("utf-8"))
print("keys:", len(d), "1a in:", "1a" in d)
print("1a val:", d.get("1a"))
