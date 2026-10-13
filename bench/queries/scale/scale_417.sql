SELECT COUNT(*) FROM title t,movie_companies mc,cast_info ci,movie_info mi WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND t.id=mi.movie_id
