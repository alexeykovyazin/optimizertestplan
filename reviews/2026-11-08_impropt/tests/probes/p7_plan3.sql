connect 'probe7' user SYSDBA;
set explain on; set planonly on;
select l.id from l where l.g >= 1 order by l.id;
select l.id, h.f from l join h on h.k = l.id2 where l.g >= 1 and h.f < 50 order by l.id;
select l.id, h.f from l join h on h.k = l.id2 where l.g >= 1 and h.f < 80 order by l.id;
select count(*) from l;
select count(*) from h;
