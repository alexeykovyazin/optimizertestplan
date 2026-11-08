connect 'probe7' user SYSDBA;
set stats on;
select count(*) as ref_f0 from h where k between 4499991 and 4500000 and f < 1;
select count(*) as ref_f01 from h where k between 4499991 and 4500000 and f < 2;
-- rescan: the BHJ is re-opened per outer row of the correlated subquery
select r.x, (select count(*) from l join h on h.k = l.id2 where h.f < r.x) c from (select 1 x from rdb$database union all select 2 from rdb$database) r;
set term ^;
-- empty leader (no H row has f < -1): the hashed side must not be read
execute block returns (p int, c bigint) as begin p = -1; select count(*) from l join h on h.k = l.id2 where h.f < :p into c; suspend; p = 1; select count(*) from l join h on h.k = l.id2 where h.f < :p into c; suspend; end^
set term ;^
