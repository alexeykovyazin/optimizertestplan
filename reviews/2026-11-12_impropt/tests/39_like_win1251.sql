-- 39_like_win1251.sql - W6 (6eb286744f, 969c21dfc3): WIN1251 client, UTF8 column, LIKE with a Cyrillic prefix and an inner wildcard.
-- PREPARE fails: Cannot transliterate character between character sets. File encoding: WIN1251. Alias tst9w1251.
-- p6: LIKE with a literal prefix and an interior wildcard over a UTF8 column, WIN1251 connection.
-- The prefix twin literal keeps the pattern charset (WIN1251 bytes); the selectivity code reads it as UTF8.
set names win1251;
create database 'tst9w1251' user SYSDBA default character set utf8;
create table t (id int, s varchar(30) character set utf8);
commit;
alter database add extended statistics;
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 5000) do begin
    insert into t values (:i, iif(mod(:i, 2) = 0, 'Мо' || :i || 'а', 'Ab' || :i));
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_s on t(s);
commit;
alter database refresh statistics;
commit;
connect 'tst9w1251' user SYSDBA;
set plan on;
select 'C1' tag, count(*) from t where s like 'Мо%а';
select 'C2' tag, count(*) from t where s like 'Мо%';
select 'C3' tag, count(*) from t where s like 'Мо1%а';
select 'C4' tag, count(*) from t where s like '%о%а';
select 'C5' tag, count(*) from t where s like 'Мо_а%';
select 'C6' tag, count(*) from t where s like 'Ab1%2';
select 'C7' tag, count(*) from t where s||'' like 'Мо%а';
set planonly on;
select 'C8' tag, count(*) from t where s like 'Мо%а';
set planonly on;
select 'D1' tag, count(*) from t where s like 'Мо0а';
select 'D2' tag, count(*) from t where s = 'Мо0а';
select 'D3' tag, count(*) from t where s starting with 'Мо1';
select 'D4' tag, count(*) from t where s containing 'о1';
select 'D5' tag, count(*) from t where s like '%о1%';
select 'D6' tag, count(*) from t where s like 'М%о';
select 'D7' tag, count(*) from t where s > 'Мо1';
select 'D8' tag, count(*) from t where s similar to 'Мо%а';
