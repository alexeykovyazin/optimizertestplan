connect 'probe7' user SYSDBA;
select count(*) as correct2 from h where k between 4499991 and 4499999 and f < 2;
set explain on;
-- in-memory HJ (hashed side < 4M): no restart expected
select count(*), sum(iif(g = 0, 1, 0)) as g0, sum(iif(f >= 2, 1, 0)) as f2, min(d) as min_d from (
  select id, g, f, id - lag(id) over () d from (select l.id, l.g, h.f from l join h on h.k = l.id2 where l.g >= 1 and h.f < 2 order by l.id) x) y;
-- restart path, no local filters: count must equal 9000 + 1000 (k = 4500000)
select count(*), min(d) as min_d from (
  select id, id - lag(id) over () d from (select l.id from l join h on h.k = l.id2 order by l.id) x) y;
