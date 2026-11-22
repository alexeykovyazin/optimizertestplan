-- Test 74: the second execution of a request with Hash Unique crashes the server (regression of b6f5cabd4b).
-- Review: REVIEW-hash-aggregate.md, finding D1.
-- Cause: HashUniqueStream::internalOpen creates a Sort (impure->diddler) registered in request->req_sorts;
-- close() does not delete it. The owner of the sorts deletes it when the request ends, the pointer stays, the next
-- open deletes it again.
-- The alias has no special settings (AggregateHashMemory = 8M by default). With AggregateHashMemory = 0: no crash.
-- Expected: three rows "call N 2", then both tables are created and "T 2" is returned.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table c (n char(10), m varchar(10), k int);
insert into c values ('a', 'a', 1);
insert into c values ('b', 'b', 2);
insert into c values ('a', 'a', 1);
commit;
set term ^;
create procedure p returns (n int) as
begin
  select count(*) from (select distinct k from c) into :n;
  suspend;
end^
set term ;^
commit;
select 'call 1' as t, n from p;
select 'call 2' as t, n from p;
select 'call 3' as t, n from p;
create table t1 (id int not null primary key, v int);
create table t2 (id int not null primary key, v int);
commit;
select 'T' as t, count(*) from rdb$relations where rdb$relation_name in ('T1', 'T2');
commit;
drop database;
