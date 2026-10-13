SELECT COUNT(*) FROM title t,movie_companies mc,cast_info ci WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND t.production_year=1966 AND ci.person_id>3377109 AND ci.role_id>2
