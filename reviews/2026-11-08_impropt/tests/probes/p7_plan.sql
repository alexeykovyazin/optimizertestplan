connect 'probe7' user SYSDBA;
set explain on; set planonly on;
-- Q1: navigated leader L, hashed H > 4M, with local filters on both
select l.id, h.f from l join h on h.k = l.id2 where l.g >= 1 and h.f < 99 order by l.id;
-- Q2: same without ORDER BY
select count(*) from l join h on h.k = l.id2 where l.g >= 1 and h.f < 99;
-- Q3: join on the indexed column
select l.id, h.f from l join h on h.k = l.id where l.g >= 1 and h.f < 99 order by l.id;
-- Q4: no filters
select l.id, h.f from l join h on h.k = l.id2 order by l.id;
