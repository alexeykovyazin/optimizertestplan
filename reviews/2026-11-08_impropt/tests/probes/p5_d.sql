connect 'probe5' user SYSDBA;
set echo on;
set planonly on; set explain on;
-- MCV value, real 5
select count(*) from tzi where y = 6596;
-- range over 100 MCV values, real 500
select count(*) from tzi where y between 6596 and 6695;
-- same width range without MCV, real 500
select count(*) from tzi where y between 12000 and 12099;
