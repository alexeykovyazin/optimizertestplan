CREATE TABLE kind_type (
  id INTEGER NOT NULL,
  kind VARCHAR(15) NOT NULL
);

CREATE TABLE comp_cast_type (
  id INTEGER NOT NULL,
  kind VARCHAR(32) NOT NULL
);

CREATE TABLE company_type (
  id INTEGER NOT NULL,
  kind VARCHAR(32) NOT NULL
);

CREATE TABLE info_type (
  id INTEGER NOT NULL,
  info VARCHAR(32) NOT NULL
);

CREATE TABLE link_type (
  id INTEGER NOT NULL,
  link VARCHAR(32) NOT NULL
);

CREATE TABLE role_type (
  id INTEGER NOT NULL,
  role VARCHAR(32) NOT NULL
);

CREATE TABLE keyword (
  id INTEGER NOT NULL,
  keyword VARCHAR(96) NOT NULL,
  phonetic_code VARCHAR(5)
);

CREATE TABLE aka_name (
  id INTEGER NOT NULL,
  person_id INTEGER NOT NULL,
  name VARCHAR(256) NOT NULL,
  imdb_index VARCHAR(12),
  name_pcode_cf VARCHAR(5),
  name_pcode_nf VARCHAR(5),
  surname_pcode VARCHAR(5),
  md5sum VARCHAR(32)
);

CREATE TABLE aka_title (
  id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  title VARCHAR(640) NOT NULL,
  imdb_index VARCHAR(12),
  kind_id INTEGER NOT NULL,
  production_year INTEGER,
  phonetic_code VARCHAR(5),
  episode_of_id INTEGER,
  season_nr INTEGER,
  episode_nr INTEGER,
  note VARCHAR(96),
  md5sum VARCHAR(32)
);

CREATE TABLE cast_info (
  id INTEGER NOT NULL,
  person_id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  person_role_id INTEGER,
  note VARCHAR(1024),
  nr_order INTEGER,
  role_id INTEGER NOT NULL
);

CREATE TABLE char_name (
  id INTEGER NOT NULL,
  name VARCHAR(512) NOT NULL,
  imdb_index VARCHAR(12),
  imdb_id INTEGER,
  name_pcode_nf VARCHAR(5),
  surname_pcode VARCHAR(5),
  md5sum VARCHAR(32)
);

CREATE TABLE company_name (
  id INTEGER NOT NULL,
  name VARCHAR(192) NOT NULL,
  country_code VARCHAR(255),
  imdb_id INTEGER,
  name_pcode_nf VARCHAR(5),
  name_pcode_sf VARCHAR(5),
  md5sum VARCHAR(32)
);

CREATE TABLE complete_cast (
  id INTEGER NOT NULL,
  movie_id INTEGER,
  subject_id INTEGER NOT NULL,
  status_id INTEGER NOT NULL
);

CREATE TABLE movie_companies (
  id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  company_id INTEGER NOT NULL,
  company_type_id INTEGER NOT NULL,
  note VARCHAR(256)
);

CREATE TABLE movie_info (
  id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  info_type_id INTEGER NOT NULL,
  info BLOB SUB_TYPE TEXT NOT NULL,
  note VARCHAR(512)
);

CREATE TABLE movie_info_idx (
  id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  info_type_id INTEGER NOT NULL,
  info VARCHAR(16) NOT NULL,
  note VARCHAR(64)
);

CREATE TABLE movie_keyword (
  id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  keyword_id INTEGER NOT NULL
);

CREATE TABLE movie_link (
  id INTEGER NOT NULL,
  movie_id INTEGER NOT NULL,
  linked_movie_id INTEGER NOT NULL,
  link_type_id INTEGER NOT NULL
);

CREATE TABLE name (
  id INTEGER NOT NULL,
  name VARCHAR(128) NOT NULL,
  imdb_index VARCHAR(12),
  imdb_id INTEGER,
  gender VARCHAR(1),
  name_pcode_cf VARCHAR(5),
  name_pcode_nf VARCHAR(5),
  surname_pcode VARCHAR(5),
  md5sum VARCHAR(32)
);

CREATE TABLE person_info (
  id INTEGER NOT NULL,
  person_id INTEGER NOT NULL,
  info_type_id INTEGER NOT NULL,
  info BLOB SUB_TYPE TEXT NOT NULL,
  note VARCHAR(512)
);

CREATE TABLE title (
  id INTEGER NOT NULL,
  title VARCHAR(384) NOT NULL,
  imdb_index VARCHAR(12),
  kind_id INTEGER NOT NULL,
  production_year INTEGER,
  imdb_id INTEGER,
  phonetic_code VARCHAR(5),
  episode_of_id INTEGER,
  season_nr INTEGER,
  episode_nr INTEGER,
  series_years VARCHAR(49),
  md5sum VARCHAR(32)
);

