-- 41_range_param_desc.sql - W8 (descending index range = constant) and W9 (82eccd50a7: parameter first in a range group). Alias tst9rg.
-- vE rg: finding 1 (parameter first in a range group) and finding 2 (descending index range estimate)
create database 'tst9rg' user SYSDBA page_size 8192;
alter database add extended statistics; commit;
create table r (x int, y int, xi int, xd int, k int);
create table s (id int not null primary key, v int, pad varchar(100));
commit;
set term ^;
execute block as declare i int = 1; begin
  while (i <= 100000) do begin
    insert into r values(:i, :i, :i, :i, mod(:i, 50000) + 1);
    insert into s values(:i, :i, lpad('', 100, 'z'));
    i = i + 1;
  end
end^
set term ;^
commit;
create index r_xi on r(xi);
create descending index r_xd on r(xd);
commit;
alter database refresh statistics; commit;
connect 'tst9rg' user SYSDBA;
set explain on;
set planonly on;
-- A: finding 1 (no index on x, y)
-- A0 x > ? alone / x > 10 alone (real 99990)
select 'A0' q, count(*) from r where x > ?;
select 'A0b' q, count(*) from r where x > 10;
-- A1 order dependence
select 'A1' q, count(*) from r where x > ? and x > 10;
select 'A1b' q, count(*) from r where x > 10 and x > ?;
-- A2 three bounds
select 'A2' q, count(*) from r where x < ? and x < 100 and x > 50;
select 'A2b' q, count(*) from r where x < 100 and x > 50 and x < ?;
-- A3 two columns, each first is a parameter
select 'A3' q, count(*) from r where x > ? and x > 10 and y > ? and y > 10;
select 'A3b' q, count(*) from r where x > 10 and x > ? and y > 10 and y > ?;
-- A4 two parameters then literal
select 'A4' q, count(*) from r where x >= ? and x <= ? and x > 10;
select 'A4b' q, count(*) from r where x > 10 and x >= ? and x <= ?;
-- A5 join: order of the filters changes the join estimate
select 'A5' q, count(*) from r join s on s.id = r.k where r.x < ? and r.x < 50000;
select 'A5b' q, count(*) from r join s on s.id = r.k where r.x < 50000 and r.x < ?;
set planonly off;
set stats on;
-- B: finding 2 (xi asc index, xd desc index, same values)
select 'B1' q, count(*) from r where xi > 10;
select 'B1d' q, count(*) from r where xd > 10;
select 'B2' q, count(*) from r where xi <= 80000;
select 'B2d' q, count(*) from r where xd <= 80000;
select 'B3' q, count(*) from r where xi < 100;
select 'B3d' q, count(*) from r where xd < 100;
select 'B4' q, count(*) from r where xi between 10 and 20;
select 'B4d' q, count(*) from r where xd between 10 and 20;
select 'B5' q, count(*) from r where xi > 5 and xi < 90000;
select 'B5d' q, count(*) from r where xd > 5 and xd < 90000;
-- B6 join, plan impact
select 'B6' q, count(*) from r join s on s.id = r.k where r.xi > 10;
select 'B6d' q, count(*) from r join s on s.id = r.k where r.xd > 10;
select 'B6' q, count(*) from r join s on s.id = r.k where r.xi > 10;
select 'B6d' q, count(*) from r join s on s.id = r.k where r.xd > 10;
select 'B7' q, count(*) from s join r on r.k = s.v where r.xi > 1000 and s.v < 30000;
select 'B7d' q, count(*) from s join r on r.k = s.v where r.xd > 1000 and s.v < 30000;
connect 'tst9rg' user SYSDBA;
set explain on; set stats on;
-- B8: two-sided range on desc index in a join (real 89994 / 1999)
select 'B8' q, count(*) from r join s on s.id = r.k where r.xi > 5 and r.xi < 90000;
select 'B8d' q, count(*) from r join s on s.id = r.k where r.xd > 5 and r.xd < 90000;
select 'B8' q, count(*) from r join s on s.id = r.k where r.xi > 5 and r.xi < 90000;
select 'B8d' q, count(*) from r join s on s.id = r.k where r.xd > 5 and r.xd < 90000;
select 'B9' q, count(*) from r join s on s.id = r.k where r.xi between 1000 and 2999;
select 'B9d' q, count(*) from r join s on s.id = r.k where r.xd between 1000 and 2999;
