SELECT COUNT(*) FROM title t,movie_companies mc,cast_info ci WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND mc.company_id>179807 AND ci.person_id<1590332 AND ci.role_id<8
