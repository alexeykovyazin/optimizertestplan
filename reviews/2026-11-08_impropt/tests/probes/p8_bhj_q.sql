connect 'probe8' user SYSDBA;
select (select count(*) from ba) ba, (select count(*) from bb) bb from rdb$database;
set explain on;
set planonly on;
-- R1: ordered, leader navigates ba_x, bb hashed (> 4M)
select count(*), sum(x) from (select ba.x, bb.g from ba join bb on bb.id = ba.id where ba.x < 2500000 order by ba.x rows 1000000000);
-- R2: control without ORDER BY
select count(*), sum(x) from (select ba.x, bb.g from ba join bb on bb.id = ba.id where ba.x < 2500000);
-- R3: plain ordered select
select ba.x, bb.g from ba join bb on bb.id = ba.id where ba.x < 2500000 order by ba.x;
