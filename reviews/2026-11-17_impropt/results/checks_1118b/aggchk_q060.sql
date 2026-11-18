set stat on;
set plan on;
SELECT SUM(a.c * b.c * c.c * d.c) FROM title t
 JOIN (SELECT movie_id, COUNT(*) c FROM movie_info WHERE info_type_id=16 GROUP BY movie_id) a ON a.movie_id=t.id
 JOIN (SELECT movie_id, COUNT(*) c FROM movie_companies GROUP BY movie_id) b ON b.movie_id=t.id
 JOIN (SELECT movie_id, COUNT(*) c FROM cast_info WHERE role_id=2 GROUP BY movie_id) c ON c.movie_id=t.id
 JOIN (SELECT movie_id, COUNT(*) c FROM movie_keyword GROUP BY movie_id) d ON d.movie_id=t.id
WHERE t.production_year>2000;
