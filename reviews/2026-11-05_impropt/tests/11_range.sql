connect 'tst2' user SYSDBA;
set planonly on;
set explain on;
select count(*) from tz where x between 50000 and 50999;
select count(*) from tz where x >= 50000 and x <= 50999;
select count(*) from tz where x >= 50000;
select count(*) from tz where x <= 50999;
select count(*) from tz where x = 50000;
