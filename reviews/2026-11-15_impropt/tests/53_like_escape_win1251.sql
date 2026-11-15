-- 53_like_escape_win1251.sql - fix y4: WIN1251 client, UTF8 column, wildcard-less and escaped Cyrillic
-- LIKE patterns no longer fail PREPARE with 'string right truncation'. Alias tst10w1251.
-- FILE IN WIN1251. Delete the old tst10w1251 database file first. Reference: sum(iif(s like ..)) (no twin).
set names win1251;
set bail off;
create database 'tst10w1251' user SYSDBA default character set utf8;
create table t (id int, s varchar(40));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 35) do begin
    insert into t values (:i, decode(mod(:i, 7), 0, 'Мо_а', 1, 'Мо_а', 2, 'Мо%а', 'Мо0а'));
    i = i + 1;
  end
end^
set term ;^
commit;
connect 'tst10w1251' user SYSDBA;
-- data: 'Мо_а' 10 rows, 'Мо%а' 5 rows, 'Мо0а' 20 rows
set list on;
select 'E1 Мо\_а esc \ (expected 10)' tag, count(*) cnt, (select sum(iif(s like 'Мо\_а' escape '\', 1, 0)) from t) truth from t where s like 'Мо\_а' escape '\';
select 'E2 Мо\%а esc \ (expected 5)' tag, count(*) cnt, (select sum(iif(s like 'Мо\%а' escape '\', 1, 0)) from t) truth from t where s like 'Мо\%а' escape '\';
select 'E3 Мо!_а esc ! (expected 10)' tag, count(*) cnt, (select sum(iif(s like 'Мо!_а' escape '!', 1, 0)) from t) truth from t where s like 'Мо!_а' escape '!';
select 'E4 Мо0а no mask (expected 20)' tag, count(*) cnt, (select sum(iif(s like 'Мо0а', 1, 0)) from t) truth from t where s like 'Мо0а';
select 'E5 Мо_а mask (expected 35)' tag, count(*) cnt, (select sum(iif(s like 'Мо_а', 1, 0)) from t) truth from t where s like 'Мо_а';
select 'E6 Мо\_% esc \ (expected 10)' tag, count(*) cnt, (select sum(iif(s like 'Мо\_%' escape '\', 1, 0)) from t) truth from t where s like 'Мо\_%' escape '\';
select 'E7 empty pattern (expected 0)' tag, count(*) cnt, (select sum(iif(s like '', 1, 0)) from t) truth from t where s like '';
select 'E8 М one char (expected 0)' tag, count(*) cnt, (select sum(iif(s like 'М', 1, 0)) from t) truth from t where s like 'М';
set list off;
create index t_s on t (s);
commit;
connect 'tst10w1251' user SYSDBA;
set list on;
select 'I1 Мо\_а esc \ idx (expected 10)' tag, count(*) cnt from t where s like 'Мо\_а' escape '\';
select 'I2 Мо0а idx (expected 20)' tag, count(*) cnt from t where s like 'Мо0а';
select 'I3 Мо\%а esc \ idx (expected 5)' tag, count(*) cnt from t where s like 'Мо\%а' escape '\';
set list off;
