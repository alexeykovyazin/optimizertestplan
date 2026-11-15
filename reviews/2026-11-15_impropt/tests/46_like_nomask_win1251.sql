-- 46_like_nomask_win1251.sql - Y4 (4be3c61de6): WIN1251 client, UTF8 column, LIKE with Cyrillic literal and no wildcards -> PREPARE fails 'string right truncation, expected length 0, actual 1'. Alias tst10w1251.
-- FILE IN WIN1251. Data: 1000 rows, s = 'Мо' || mod(i, 4) || 'а' -> each value 250 rows. No index first, then with index.
-- Expected: s like 'Мо0а' -> 250 (arithmetic). Controls: 'Мо0%' and s = 'Мо0а' -> 250.
set names win1251;
set bail off;
create database 'tst10w1251' user SYSDBA default character set utf8;
create table t (id int, s varchar(40));
commit;
set term ^;
execute block as declare i int = 0; begin
  while (i < 1000) do begin insert into t values (:i, 'Мо' || mod(:i, 4) || 'а'); i = i + 1; end
end^
set term ;^
commit;
connect 'tst10w1251' user SYSDBA;

select 'R1 s = ''Мо0а'' expected (250)' as tag, count(*) as expected from t where s = 'Мо0а';

set planonly on;
select count(*) from t where s like 'Мо0а';
set planonly off;
set plan off;

select 'Q1 s like ''Мо0а'' (no index)' as tag, count(*) as cnt from t where s like 'Мо0а';
select 'Q2 s like ''Мо0а'' escape ''!'' (no index)' as tag, count(*) as cnt from t where s like 'Мо0а' escape '!';
-- controls
select 'C1 s like ''Мо0%'' (expected 250)' as tag, count(*) as cnt from t where s like 'Мо0%';
select 'C2 s like ''Мо0_'' (expected 250)' as tag, count(*) as cnt from t where s like 'Мо0_';
select 'C3 s like ''Ab'' ASCII (expected 0)' as tag, count(*) as cnt from t where s like 'Ab';

create index t_s on t (s);
commit;
connect 'tst10w1251' user SYSDBA;
select 'I1 s like ''Мо0а'' (index)' as tag, count(*) as cnt from t where s like 'Мо0а';
select 'I2 s like ''Мо0%'' (index, expected 250)' as tag, count(*) as cnt from t where s like 'Мо0%';
