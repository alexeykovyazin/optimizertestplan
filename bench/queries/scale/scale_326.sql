SELECT COUNT(*) FROM title t,movie_companies mc,cast_info ci,movie_info_idx mi_idx WHERE t.id=mc.movie_id AND t.id=ci.movie_id AND t.id=mi_idx.movie_id AND ci.person_id<3666974 AND ci.role_id>1
