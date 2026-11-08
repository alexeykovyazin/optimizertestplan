-- 32_like_crash.sql - a3cfa97218 (ab9730e98b): the server process stops
-- (access violation) when it prepares LIKE '%_%' on a VARCHAR column with
-- the length distribution collected. Only PREPARE is needed (SET PLANONLY).
-- f2888abf7c prints the plans. a3cfa97218 stops at the first LIKE below
-- (embedded isql exits with rc=3, firebird.log: "Access violation").
-- Alias tst8like: ExtendedStatistics = true, ShowExplainCardinality = true.
create database 'tst8like' user SYSDBA;
create table pn(id int, nm varchar(40));
set term ^;
execute block as declare i int = 0; begin
  while (i < 20000) do begin
    insert into pn values(:i, decode(mod(:i, 5), 0, 'Smith', 1, 'Anderson', 2, 'Li', 3, 'Kowalski', 'Mary Ann') || ' ' || :i);
    i = i + 1;
  end
end^
set term ;^
commit;
alter database add extended statistics;
commit;
alter database refresh statistics;
commit;

set planonly on;
select 'before' from rdb$database;
-- the patterns that work
select count(*) from pn where nm like '%an%';
select count(*) from pn where nm like '%a_%';
-- the patterns that stop the server: '%_%', '_%', '___', '%__%'
select count(*) from pn where nm like '%_%';
select 'after' from rdb$database;
