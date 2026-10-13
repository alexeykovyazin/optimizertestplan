SELECT COUNT(*) FROM title t,movie_companies mc,movie_info mi,movie_keyword mk WHERE t.id=mc.movie_id AND t.id=mi.movie_id AND t.id=mk.movie_id AND t.production_year=1940 AND mi.info_type_id>16
