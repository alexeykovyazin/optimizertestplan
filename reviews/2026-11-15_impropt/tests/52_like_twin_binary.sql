-- 52_like_twin_binary.sql - fix y2: the equality twin of a wildcard-less LIKE stays only under the binary
-- default collation with the pattern in the column charset; elsewhere the starting twin. Alias tst10like.
-- File in UTF8. Delete the old tst10like database file first. Reference: sum(iif(col like ..)) (no twin there).
set names utf8;
set bail off;
create database 'tst10like' user SYSDBA default character set utf8;
create table b (id int, s varchar(20), c char(10), w varchar(20) character set win1251,
  ci varchar(20) collate unicode_ci);
commit;
insert into b values (1, 'abc', 'abc', 'abc', 'smith');
insert into b values (2, 'abc ', 'abc ', 'abc ', 'SMITH');
insert into b values (3, 'ABC', 'ABC', 'ABC', 'Smith');
insert into b values (4, 'abcd', 'abcd', 'abcd', 'smithy');
insert into b values (5, 'Мо0а', 'Мо0а', 'Мо0а', 'Мо0а');
commit;
connect 'tst10like' user SYSDBA;
set list on;
select 'B1 s like abc (expected 1)' tag, count(*) cnt, (select sum(iif(s like 'abc', 1, 0)) from b) truth from b where s like 'abc';
select 'B2 s like abc_space (expected 1)' tag, count(*) cnt, (select sum(iif(s like 'abc ', 1, 0)) from b) truth from b where s like 'abc ';
select 'B3 c char(10) like abc (cnt = truth, as BASE)' tag, count(*) cnt, (select sum(iif(c like 'abc', 1, 0)) from b) truth from b where c like 'abc';
select 'B4 c char(10) like abc+7 spaces (cnt = truth, as BASE)' tag, count(*) cnt, (select sum(iif(c like 'abc       ', 1, 0)) from b) truth from b where c like 'abc       ';
select 'B5 s like Cyrillic (expected 1)' tag, count(*) cnt, (select sum(iif(s like 'Мо0а', 1, 0)) from b) truth from b where s like 'Мо0а';
select 'B6 w win1251 col, utf8 literal (expected 1)' tag, count(*) cnt, (select sum(iif(w like 'Мо0а', 1, 0)) from b) truth from b where w like 'Мо0а';
select 'B7 ci unicode_ci like smith (expected 3)' tag, count(*) cnt, (select sum(iif(ci like 'smith', 1, 0)) from b) truth from b where ci like 'smith';
set list off;
create index b_s on b (s);
create index b_ci on b (ci);
commit;
connect 'tst10like' user SYSDBA;
set list on;
select 'I1 s like abc idx (expected 1)' tag, count(*) cnt from b where s like 'abc';
select 'I2 ci like smith idx (expected 3)' tag, count(*) cnt from b where ci like 'smith';
set list off;
-- plans: s (binary) keeps the equality twin - Range Scan (full match) on B_S, as before the fix;
-- ci (UNICODE_CI) gets the starting twin - the range scan on B_CI as on the stock build
set explain on;
set planonly on;
select count(*) from b where s like 'abc';
select count(*) from b where ci like 'smith';
set planonly off;
