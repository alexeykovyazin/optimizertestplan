SELECT COUNT(*) FROM title t,cast_info ci,movie_keyword mk WHERE t.id=ci.movie_id AND t.id=mk.movie_id AND t.production_year<1938 AND ci.person_id<2290872 AND ci.role_id>1
