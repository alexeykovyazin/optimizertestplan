import os
import subprocess

q = ("SELECT n.id, n.name, t.id, t.production_year, t.kind_id, kt.kind, "
     "ci.role_id, rt.role FROM title t, kind_type kt, movie_info mi1, "
     "info_type it1, cast_info ci, role_type rt, name n "
     "WHERE t.id=ci.movie_id AND t.id=mi1.movie_id AND mi1.info_type_id=it1.id "
     "AND t.kind_id=kt.id AND ci.person_id=n.id AND ci.movie_id=mi1.movie_id "
     "AND ci.role_id=rt.id AND it1.id=6 AND mi1.info='Mono' "
     "AND n.name ILIKE '%kowal%' AND n.name='Kowalski, Lech' "
     "AND kt.kind IN ('episode','movie','tv movie') "
     "AND rt.role IN ('director','editor','producer') ORDER BY t.id")
r = subprocess.run(
    ["ssh", "dellg15",
     f'set PGPASSWORD={os.environ["BENCH_PG_PWD"]}&& '
     'C:\\pgsql\\bin\\psql.exe -U postgres -d imdb '
     f'-A -t -q -c "{q}"'],
    capture_output=True, text=True)
print(r.stdout[:3000])
print("ERR:", r.stderr[:300])
