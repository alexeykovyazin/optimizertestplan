SELECT COUNT(*) FROM title t,movie_companies mc,cast_info ci,movie_keyword mk WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND t.id=mk.movie_id AND t.kind_id=7 AND t.production_year>2012
