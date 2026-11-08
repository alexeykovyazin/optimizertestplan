connect 'probe7' user SYSDBA;
drop index l_id2;
create index h_k on h(k);
commit;
set explain on;
-- GROUP BY on the navigable PK, expected: 9 groups, 7715 rows
select count(*) as grp, sum(c) as total from (select l.id, count(*) c from l join h on h.k = l.id2 where l.g >= 1 and h.f < 6 group by l.id) x;
