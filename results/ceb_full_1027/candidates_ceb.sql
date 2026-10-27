-- Кандидаты многоколоночных статистик для ceb-imdb-regen (анализ 27.10).
-- Уже существующие 19 структур (CEB-словари 26.10 + JOB/job-light пары 27.10)
-- закрывают role/kind/company_type/comp_cast/info_type/link_type словари,
-- TITLE(id/kind, production_year), NAME(ID, GENDER), MOVIE_INFO/IDX/COMPANIES/
-- CAST_INFO/KEYWORD пары. Новое — только специфичное для ceb:

-- name: join по ID (ci.person_id = n.id) + IN-списки/IS NULL по pcode
CREATE EXTENDED STATISTICS STAT_NAME_ID_NAME_PCODE_NF ON NAME(ID, NAME_PCODE_NF);
CREATE EXTENDED STATISTICS STAT_NAME_ID_SURNAME_PCODE ON NAME(ID, SURNAME_PCODE);
-- name: совместная селективность двух фильтров (gender + pcode), без ID
CREATE EXTENDED STATISTICS STAT_NAME_GENDER_PCODE_NF ON NAME(GENDER, NAME_PCODE_NF);
-- movie_info_idx: join по MOVIE_ID + фильтр по varchar info (15 запросов)
CREATE EXTENDED STATISTICS STAT_MOVIE_INFO_IDX_MID_INFO ON MOVIE_INFO_IDX(MOVIE_ID, INFO);

-- После CREATE: ALTER DATABASE REFRESH STATISTICS;
