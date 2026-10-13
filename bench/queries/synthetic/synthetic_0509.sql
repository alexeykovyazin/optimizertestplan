SELECT COUNT(*) FROM title t,movie_companies mc,cast_info ci WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND t.production_year>0 AND mc.company_id<30240 AND mc.company_type_id<2
