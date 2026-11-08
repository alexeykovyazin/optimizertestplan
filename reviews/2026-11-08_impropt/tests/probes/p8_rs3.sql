connect 'probe8' user SYSDBA;
set count on;
set stats on;
-- T3 executed: expected 36000 rows, max rc.x = 600000
select rc.x from rc join rb on rb.g = rc.g where rc.x < 600001 order by rc.x;
