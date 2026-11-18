set stat on;
SELECT COUNT(*) n, SUM(a.c) sa, SUM(b.c) sb, SUM(c.c) sc, SUM(d.c) sd,
       SUM(c.c * d.c) s_ci_mk, SUM(a.c * c.c * d.c) s_mi_ci_mk, SUM(a.c * b.c * c.c * d.c) s_all
FROM (SELECT movie_id, COUNT(*) c FROM movie_info GROUP BY movie_id) a
 JOIN (SELECT movie_id, COUNT(*) c FROM movie_companies GROUP BY movie_id) b ON b.movie_id=a.movie_id
 JOIN (SELECT movie_id, COUNT(*) c FROM cast_info GROUP BY movie_id) c ON c.movie_id=a.movie_id
 JOIN (SELECT movie_id, COUNT(*) c FROM movie_keyword GROUP BY movie_id) d ON d.movie_id=a.movie_id;
