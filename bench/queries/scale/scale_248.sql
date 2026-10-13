SELECT COUNT(*) FROM title t,movie_companies mc,movie_info mi,movie_keyword mk WHERE t.id=mc.movie_id AND t.id=mi.movie_id AND t.id=mk.movie_id AND mi.info_type_id>4 AND mk.keyword_id=51157
