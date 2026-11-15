-- 45_like_eq_twin_translit.sql - Y3 (381231c716): LIKE equality twin keeps the literal in the client charset; WIN1251 client, UTF8 column with a CJK char -> 'Cannot transliterate' at execution. Alias tst10tr.
-- Data: UTF8 database, t.s = 'abc', 'abd', U+4E2D (inserted as _utf8 x'E4B8AD'). No index on s.
-- Expected: s like 'abc' -> 1 row (BASE gives 1). The error is at execution; PREPARE (planonly) passes.
set names utf8;
set bail off;
create database 'tst10tr' user SYSDBA default character set utf8;
create table t (id int, s varchar(20));
commit;
insert into t values (1, 'abc');
insert into t values (2, 'abd');
insert into t values (3, _utf8 x'E4B8AD');
commit;
set names win1251;
connect 'tst10tr' user SYSDBA;

select 'R1 expected (1)' as tag, sum(iif(s like 'abc', 1, 0)) as expected from t;
select 'R2 octet_length of row 3 (3 = one CJK char)' as tag, octet_length(s) as len from t where id = 3;

set explain on;
set planonly on;
select count(*) from t where s like 'abc';
set planonly off;
set explain off;
set plan off;

select 'Q1 s like ''abc'' (no index)' as tag, count(*) as cnt from t where s like 'abc';
-- controls
select 'C1 s like ''ab%'' (expected 2)' as tag, count(*) as cnt from t where s like 'ab%';
select 'C2 s starting with ''abc'' (expected 1)' as tag, count(*) as cnt from t where s starting with 'abc';
-- note: on BASE plain s = 'abc' also fails here (old defect of =); the twin moves it to LIKE
select 'C3 s = ''abc'' (old defect of =)' as tag, count(*) as cnt from t where s = 'abc';

-- with an index the query works on all builds
create index t_s on t (s);
commit;
connect 'tst10tr' user SYSDBA;
select 'I1 s like ''abc'' (index, expected 1)' as tag, count(*) as cnt from t where s like 'abc';
