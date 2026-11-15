-- 44_like_eq_twin_ci.sql - Y2 (381231c716): LIKE without wildcards gets an equality twin (=) and loses rows under CI/AI collations without an index. Alias tst10ci.
-- File in UTF8. Reference: the same LIKE in the select list, sum(iif(col like ..., 1, 0)) - no twin there.
-- No index on any column: the twin works as a filter. Each column holds the same 18 values.
set names utf8;
set bail off;
create database 'tst10ci' user SYSDBA default character set utf8;
create table t (id int,
  ci varchar(20) collate unicode_ci,
  ai varchar(20) collate unicode_ci_ai,
  es varchar(20) character set iso8859_1 collate es_es_ci_ai);
commit;
insert into t values (1, 'Сергей', 'Сергей', null);
insert into t values (2, 'СЕРГЕЙ', 'СЕРГЕЙ', null);
insert into t values (3, 'Сергеи', 'Сергеи', null);
insert into t values (4, 'Майя', 'Майя', null);
insert into t values (5, 'Маия', 'Маия', null);
insert into t values (6, 'i', 'i', 'i');
insert into t values (7, 'I', 'I', 'I');
insert into t values (8, 'ı', 'ı', null);
insert into t values (9, 'Straße', 'Straße', 'Straße');
insert into t values (10, 'STRASSE', 'STRASSE', 'STRASSE');
insert into t values (11, 'strasse', 'strasse', 'strasse');
insert into t values (12, 'Strase', 'Strase', 'Strase');
insert into t values (13, 'smith', 'smith', 'smith');
insert into t values (14, 'SMITH', 'SMITH', 'SMITH');
insert into t values (15, 'Smith', 'Smith', 'Smith');
insert into t values (16, 'Иванов', 'Иванов', null);
insert into t values (17, 'ИВАНОВ', 'ИВАНОВ', null);
insert into t values (18, 'иванов', 'иванов', null);
commit;
connect 'tst10ci' user SYSDBA;

-- plan: no index, the filter is the twin
set explain on;
set planonly on;
select count(*) from t where ai like 'сергеи';
set planonly off;
set explain off;
set plan off;

-- ===== Q: cnt_like = count(*) where col like p; expected = sum(iif(col like p, 1, 0)) =====
select 'Q1 ai(UNICODE_CI_AI) like ''сергеи''' as tag,
  (select count(*) from t where ai like 'сергеи') as cnt_like,
  (select sum(iif(ai like 'сергеи', 1, 0)) from t) as expected from rdb$database;
select 'Q2 ai(UNICODE_CI_AI) like ''маия''' as tag,
  (select count(*) from t where ai like 'маия') as cnt_like,
  (select sum(iif(ai like 'маия', 1, 0)) from t) as expected from rdb$database;
select 'Q3 ci(UNICODE_CI) like ''i''' as tag,
  (select count(*) from t where ci like 'i') as cnt_like,
  (select sum(iif(ci like 'i', 1, 0)) from t) as expected from rdb$database;
select 'Q4 es(ES_ES_CI_AI) like ''Straße''' as tag,
  (select count(*) from t where es like 'Straße') as cnt_like,
  (select sum(iif(es like 'Straße', 1, 0)) from t) as expected from rdb$database;
select 'Q5 ci(UNICODE_CI) like x''736D697468'' (smith)' as tag,
  (select count(*) from t where ci like x'736D697468') as cnt_like,
  (select sum(iif(ci like x'736D697468', 1, 0)) from t) as expected from rdb$database;

-- ===== C: controls - ordinary case, the twin is correct here =====
select 'C1 ci(UNICODE_CI) like ''иванов''' as tag,
  (select count(*) from t where ci like 'иванов') as cnt_like,
  (select sum(iif(ci like 'иванов', 1, 0)) from t) as expected from rdb$database;
select 'C2 ci(UNICODE_CI) like ''smith''' as tag,
  (select count(*) from t where ci like 'smith') as cnt_like,
  (select sum(iif(ci like 'smith', 1, 0)) from t) as expected from rdb$database;
select 'C3 ai(UNICODE_CI_AI) like ''сергеи%'' (with mask, no twin)' as tag,
  (select count(*) from t where ai like 'сергеи%') as cnt_like,
  (select sum(iif(ai like 'сергеи%', 1, 0)) from t) as expected from rdb$database;
