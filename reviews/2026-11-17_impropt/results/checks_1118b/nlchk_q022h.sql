set stat on;
set plan on;
SELECT COUNT(*) FROM cast_info ci,title t WHERE t.id=ci.movie_id AND t.production_year>1980 AND t.production_year<2010 PLAN HASH (CI NATURAL, T NATURAL);
