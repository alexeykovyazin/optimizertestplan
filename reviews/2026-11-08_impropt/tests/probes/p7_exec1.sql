connect 'probe7' user SYSDBA;
set stats on;
-- reference counts from H alone (each matching key has one L row)
select count(*) as correct from h where k between 4499991 and 4499999 and f < 6;
select count(*) as h_filter_lost from h where k between 4499991 and 4499999;
select count(*) as l_filter_lost from h where k between 4499991 and 4500000 and f < 6;
set explain on;
-- no ORDER BY: BHJ without restart
select count(*) from l join h on h.k = l.id2 where l.g >= 1 and h.f < 6;
-- ORDER BY on the navigable PK: restart path
select count(*), sum(iif(g = 0, 1, 0)) as g0, sum(iif(f >= 6, 1, 0)) as f6, min(d) as min_d from (
  select id, g, f, id - lag(id) over () d from (select l.id, l.g, h.f from l join h on h.k = l.id2 where l.g >= 1 and h.f < 6 order by l.id) x) y;
