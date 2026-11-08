connect 'probe7' user SYSDBA;
set explain on; set planonly on;
select l.id, h.f from l join h on h.k = l.id2 where l.g >= 1 and h.f < 6 order by l.id;
select count(*) from l join h on h.k = l.id2 where l.g >= 1 and h.f < 6;
