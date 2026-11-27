set bail off;
create database 'cf1' user SYSDBA default character set utf8;
create table p (id int not null primary key, k int, j int, x int, n numeric(10,2), s varchar(10), ci varchar(10) collate unicode_ci);
create table c (id int not null primary key, k int, j int, x int, n numeric(10,2), s varchar(10), ci varchar(10) collate unicode_ci);
create table d (id int not null primary key, k int, j int, x int, n numeric(10,2), s varchar(10), ci varchar(10) collate unicode_ci);
create table e (id int not null primary key, k int, j int, x int);
create table u (id int not null primary key, j int);
commit;
set term ^;
execute block as
  declare i int = 1;
  declare h int;
begin
  while (i <= 2000) do
  begin
    h = mod(i * 7919 + 13, 100003);
    insert into p (id, k, j, x, n, s, ci) values (:i,
      iif(mod(:i, 10) = 0, null, mod(:h, 60)),
      iif(mod(:i, 7) = 0, null, mod(:h, 5)),
      mod(:i, 4),
      iif(mod(:i, 13) = 0, null, mod(:h, 60) + iif(mod(:h, 6) = 0, 0.50, 0)),
      iif(mod(:i, 11) = 0, null, iif(mod(:h, 3) = 0, 'a', iif(mod(:h, 3) = 1, 'A', 'b '))),
      iif(mod(:i, 17) = 0, null, iif(mod(:h, 3) = 0, 'a', iif(mod(:h, 3) = 1, 'A', 'c'))));
    i = i + 1;
  end
  i = 1;
  while (i <= 3000) do
  begin
    h = mod(i * 104729 + 7, 100019);
    insert into c (id, k, j, x, n, s, ci) values (:i,
      iif(mod(:i, 9) = 0, null, mod(:h, 40) * 2),
      iif(mod(:i, 5) = 0, null, mod(:h, 5)),
      mod(:i, 3),
      iif(mod(:i, 8) = 0, null, mod(:h, 40) * 2),
      iif(mod(:i, 6) = 0, null, iif(mod(:h, 3) = 0, 'a', iif(mod(:h, 3) = 1, 'b', 'B '))),
      iif(mod(:i, 6) = 0, null, iif(mod(:h, 3) = 0, 'a', iif(mod(:h, 3) = 1, 'b', 'B'))));
    i = i + 1;
  end
  i = 0;
  while (i <= 58) do
  begin
    insert into u (id, j) values (:i, iif(mod(:i, 4) = 0, null, mod(:i, 5)));
    i = i + 2;
  end
end^
set term ;^
commit;
insert into d select * from c;
commit;
create index c_k on c (k);
create index c_j on c (j);
create view vne as select p.id, p.k, p.j, p.x from p where not exists (select 1 from d where d.k = p.k);
create view vlj as select p.id, p.k, p.j, p.x, d.id as did, d.k as dk, d.j as dj from p left join d on d.k = p.k;
commit;
set statistics index c_k;
set statistics index c_j;
commit;
