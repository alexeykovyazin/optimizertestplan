connect 'probe6' user SYSDBA;
set planonly on;
set explain on;
select count(*) from pn where nm like '_%';
select 'after' from rdb$database;
