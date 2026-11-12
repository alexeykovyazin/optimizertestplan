-- 37_like_escape.sql - W3 (24da50c73f, 14.10): LIKE ... ESCAPE with an escaped char before the first wildcard loses rows. Alias tst9esc.
-- Finding 1: LIKE ... ESCAPE, escaped char before the first wildcard
set names utf8;
create database 'tst9esc' user SYSDBA page_size 8192 default character set utf8;
create table t(id int, s varchar(20));
set term ^;
execute block as declare i int = 0; begin
  while (i < 1000) do begin
    insert into t values(:i, decode(mod(:i, 4), 0, 'a%', 1, 'a_b', 2, 'abc%xyz', 'x' || :i));
    i = i + 1;
  end
end^
set term ;^
commit;
set list on;
-- columns: cnt = WHERE result, truth = sum(iif(...)) over all rows
select 'A1 a\% noidx' tag, count(*) cnt, (select sum(iif(s like 'a\%' escape '\', 1, 0)) from t) truth from t where s like 'a\%' escape '\';
select 'A2 a\_b noidx' tag, count(*) cnt, (select sum(iif(s like 'a\_b' escape '\', 1, 0)) from t) truth from t where s like 'a\_b' escape '\';
select 'A3 a!_b esc ! noidx' tag, count(*) cnt, (select sum(iif(s like 'a!_b' escape '!', 1, 0)) from t) truth from t where s like 'a!_b' escape '!';
select 'A4 abc|%% esc | noidx' tag, count(*) cnt, (select sum(iif(s like 'abc|%%' escape '|', 1, 0)) from t) truth from t where s like 'abc|%%' escape '|';
select 'A5 a\% plan natural' tag, count(*) cnt from t where s like 'a\%' escape '\' plan (t natural);
select 'A6 abc% no escape (control)' tag, count(*) cnt, (select sum(iif(s like 'abc%', 1, 0)) from t) truth from t where s like 'abc%';
create index t_s on t(s);
commit;
select 'B1 a\% idx' tag, count(*) cnt from t where s like 'a\%' escape '\';
select 'B2 a\_b idx' tag, count(*) cnt from t where s like 'a\_b' escape '\';
select 'B3 a!_b esc ! idx' tag, count(*) cnt from t where s like 'a!_b' escape '!';
select 'B4 abc|%% esc | idx' tag, count(*) cnt from t where s like 'abc|%%' escape '|';
select 'B5 a\% idx natural' tag, count(*) cnt from t where s like 'a\%' escape '\' plan (t natural);
set list off;
set planonly on;
select count(*) from t where s like 'a\%' escape '\';
select count(*) from t where s like 'abc|%%' escape '|';
