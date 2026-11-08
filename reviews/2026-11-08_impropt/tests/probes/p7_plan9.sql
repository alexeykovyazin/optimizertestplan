connect 'probe7' user SYSDBA;
drop index h_k;
commit;
set explain on; set planonly on;
select r.x, (select count(*) from l join h on h.k = l.id2 where h.f < r.x) from (select 1 x from rdb$database union all select 2 from rdb$database) r;
select count(*) from l join h on h.k = l.id2 where h.f < ?;
select count(*) from l join h on h.k = l.id2 where h.f <> ?;
select count(*) from l join h on h.k = l.id2 where l.g <> ?;
