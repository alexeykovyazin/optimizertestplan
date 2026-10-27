# Кандидаты многоколоночных статистик: JOB + JOB-light


## JOB

| таблица | join-колонка | фильтр | запросов | из них диапазон |
|---|---|---|---|---|
| title | id | production_year | 80 | 77 |
| keyword | id | keyword | 69 | 0 |
| company_name | id | country_code | 64 | 0 |
| info_type | id | info | 61 | 0 |
| movie_info | movie_id | info **BLOB** | 49 | 0 |
| movie_info | info_type_id | info **BLOB** | 40 | 0 |
| movie_companies | movie_id | note | 32 | 0 |
| cast_info | movie_id | note | 30 | 0 |
| cast_info | person_id | note | 27 | 0 |
| name | id | name | 27 | 0 |
| name | id | gender | 27 | 0 |
| kind_type | id | kind | 26 | 0 |
| movie_companies | company_id | note | 25 | 0 |
| movie_companies | company_type_id | note | 25 | 0 |
| company_type | id | kind | 24 | 0 |
| title | kind_id | production_year | 22 | 21 |
| comp_cast_type | id | kind | 21 | 0 |
| movie_info_idx | info_type_id | info | 21 | 21 |
| movie_info_idx | movie_id | info | 21 | 21 |
| role_type | id | role | 19 | 0 |
| cast_info | role_id | note | 18 | 0 |
| cast_info | person_role_id | note | 16 | 0 |
| company_name | id | name | 14 | 0 |
| link_type | id | link | 14 | 0 |
| name | — | gender+name | 14 | 0 |
| title | id | title | 13 | 0 |
| company_name | — | country_code+name | 11 | 0 |
| title | — | production_year+title | 11 | 10 |
| char_name | id | name | 8 | 0 |
| movie_info | info_type_id | note | 8 | 0 |
| movie_info | movie_id | note | 8 | 0 |
| movie_info | — | info+note | 7 | 0 |
| aka_name | person_id | name | 3 | 0 |
| name | — | gender+name_pcode_cf | 3 | 2 |
| name | id | name_pcode_cf | 3 | 2 |
| person_info | info_type_id | note | 3 | 0 |
| person_info | person_id | note | 3 | 0 |
| title | id | episode_nr | 3 | 3 |
| title | kind_id | title | 3 | 0 |
| name | — | name+name_pcode_cf | 2 | 2 |

## JOB-light

| таблица | join-колонка | фильтр | запросов | из них диапазон |
|---|---|---|---|---|
| title | id | production_year | 56 | 55 |
| movie_info | movie_id | info_type_id | 28 | 0 |
| movie_info_idx | movie_id | info_type_id | 26 | 0 |
| movie_companies | movie_id | company_type_id | 16 | 0 |
| cast_info | movie_id | role_id | 15 | 0 |
| movie_keyword | movie_id | keyword_id | 13 | 0 |
| title | id | kind_id | 7 | 0 |
| title | — | kind_id+production_year | 5 | 5 |
| movie_companies | movie_id | company_id | 1 | 0 |
