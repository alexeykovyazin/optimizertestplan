-- Timing database for the counted streams (local measurements).
-- t: 60 000 rows, the table of test 79 (m: 3000 values, 20 rows per value; k: 40 values).
-- dim: 2 000 rows, id is the primary key, g: 40 values, m: 2000 values (unique), h: 200 values (10 rows per value).
-- fact: 2 000 000 rows, dim_id: 2000 values (1000 rows per value), u: 1 000 000 values (2 rows per value),
--       s: 500 000 values (4 rows per value).
set bail on;
create database 'tcount' user SYSDBA default character set utf8;
create table t (id int not null primary key, k int not null, m int not null, s varchar(30), v numeric(18,2));
create table dim (id int not null primary key, g int not null, m int not null, h int not null, name varchar(30));
create table fact (id int not null primary key, dim_id int not null, u int not null, s int not null, v numeric(18,2));
set term ^;
execute block as declare i int = 0; begin
  while (i < 60000) do begin
    insert into t values (:i, mod(:i, 40), mod(:i * 7, 3000), 'name' || mod(:i, 500), :i / 3.0);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 2000) do begin
    insert into dim values (:i, mod(:i, 40), :i, mod(:i, 200), 'dim' || :i);
    i = i + 1;
  end
end^
execute block as declare i int = 0; begin
  while (i < 2000000) do begin
    insert into fact values (:i, mod(:i * 7, 2000), mod(:i * 13, 1000000), mod(:i * 11, 500000), :i / 7.0);
    i = i + 1;
  end
end^
set term ;^
commit;
create index t_k on t (k); create index t_m on t (m);
create index dim_m on dim (m); create index dim_h on dim (h); create index dim_g on dim (g);
create index fact_dim on fact (dim_id); create index fact_u on fact (u); create index fact_s on fact (s);
commit;
