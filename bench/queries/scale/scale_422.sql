SELECT COUNT(*) FROM title t,cast_info ci,movie_info mi,movie_keyword mk WHERE t.id=ci.movie_id AND t.id=mi.movie_id AND t.id=mk.movie_id AND ci.role_id>10 AND mi.info_type_id>15
