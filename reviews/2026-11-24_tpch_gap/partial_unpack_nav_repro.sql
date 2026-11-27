-- Repro: an index navigation over a two-column primary key when the query refers to the first column only.
-- P has 4 000 rows; every statement must report 4 000 records.
set bail off;
create database 'tst2def' user SYSDBA default character set utf8;
create table p (a int not null, b int not null, w int, constraint p_pk primary key (a, b));
set term ^;
execute block as declare i int = 0; begin
  while (i < 4000) do begin
    insert into p values (mod(:i, 40), :i / 40, :i);
    i = i + 1;
  end
end^
set term ;^
commit;
set count on;
set plan on;
select a from p order by a;
select w from p order by a;
select a from p order by a, b;
select a, b from p order by a, b;
select a, w from p order by a, b;
select a from p;
drop database;
