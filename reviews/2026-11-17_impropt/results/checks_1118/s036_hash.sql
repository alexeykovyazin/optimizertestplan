set stat on;
set explain on;
SELECT COUNT(*) FROM title t,cast_info ci WHERE t.id=ci.movie_id AND t.kind_id<7 PLAN HASH (CI NATURAL, T INDEX (KIND_ID_TITLE));
SELECT COUNT(*) FROM title t,cast_info ci WHERE t.id=ci.movie_id AND t.kind_id<7 PLAN HASH (CI NATURAL, T INDEX (KIND_ID_TITLE));
