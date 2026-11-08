connect 'probe7' user SYSDBA;
create table l2 (id int, id2 int);
commit;
insert into l2 select id, iif(mod(id, 99991) = 0, null, mod(id - 1, 1500000) + 3000001) from l;
commit;
alter database refresh statistics;
commit;
set stats on;
-- references
select sum(a.c * b.m) as ref_eq from (select k, count(*) c from h where k between 4499991 and 4500000 and f < 2 group by k) a join (select id2, count(*) m from l2 where id2 between 4499991 and 4500000 group by id2) b on a.k = b.id2;
select (select count(*) from h where k is null and f < 2) as h_null, (select count(*) from l2 where id2 is null) as l2_null from rdb$database;
set explain on;
set term ^;
execute block returns (c1 bigint, c2 bigint) as declare p int = 2; begin
  select count(*) from h join l2 on h.k = l2.id2 where h.f < :p into c1;
  select count(*) from h join l2 on h.k is not distinct from l2.id2 where h.f < :p into c2;
  suspend; end^
set term ;^
set planonly on;
select count(*) from h join l2 on h.k = l2.id2 where h.f < ?;
select count(*) from h join l2 on h.k is not distinct from l2.id2 where h.f < ?;
