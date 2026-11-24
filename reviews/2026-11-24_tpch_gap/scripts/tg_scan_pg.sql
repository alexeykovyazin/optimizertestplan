\pset pager off
select relpages, reltuples, pg_relation_size('lineitem') from pg_class where relname = 'lineitem';
\d lineitem
show max_parallel_workers_per_gather;
\timing on
\echo m01 count(*) no data run 1
select count(*) from lineitem;
\echo m01 count(*) no data run 2
select count(*) from lineitem;
\echo m01 count(*) no data run 3
select count(*) from lineitem;
\echo m02 count(field) unpack only run 1
select count(l_orderkey) from lineitem;
\echo m02 count(field) unpack only run 2
select count(l_orderkey) from lineitem;
\echo m02 count(field) unpack only run 3
select count(l_orderkey) from lineitem;
\echo m03 int compare first field run 1
select count(*) from lineitem where l_orderkey < 0;
\echo m03 int compare first field run 2
select count(*) from lineitem where l_orderkey < 0;
\echo m03 int compare first field run 3
select count(*) from lineitem where l_orderkey < 0;
\echo m04 numeric compare run 1
select count(*) from lineitem where l_quantity < 25;
\echo m04 numeric compare run 2
select count(*) from lineitem where l_quantity < 25;
\echo m04 numeric compare run 3
select count(*) from lineitem where l_quantity < 25;
\echo m05 one date literal run 1
select count(*) from lineitem where l_shipdate >= date '1997-01-01';
\echo m05 one date literal run 2
select count(*) from lineitem where l_shipdate >= date '1997-01-01';
\echo m05 one date literal run 3
select count(*) from lineitem where l_shipdate >= date '1997-01-01';
\echo m06 two date literals run 1
select count(*) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01';
\echo m06 two date literals run 2
select count(*) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01';
\echo m06 two date literals run 3
select count(*) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01';
\echo m09 between literals run 1
select count(*) from lineitem where l_discount between 0.05 and 0.07;
\echo m09 between literals run 2
select count(*) from lineitem where l_discount between 0.05 and 0.07;
\echo m09 between literals run 3
select count(*) from lineitem where l_discount between 0.05 and 0.07;
\echo m10 between const arithmetic run 1
select count(*) from lineitem where l_discount between 0.06 - 0.01 and 0.06 + 0.01;
\echo m10 between const arithmetic run 2
select count(*) from lineitem where l_discount between 0.06 - 0.01 and 0.06 + 0.01;
\echo m10 between const arithmetic run 3
select count(*) from lineitem where l_discount between 0.06 - 0.01 and 0.06 + 0.01;
\echo m11 q6 all literals run 1
select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.05 and 0.07 and l_quantity < 25;
\echo m11 q6 all literals run 2
select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.05 and 0.07 and l_quantity < 25;
\echo m11 q6 all literals run 3
select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.05 and 0.07 and l_quantity < 25;
\echo m12 q6 date literals run 1
select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.06 - 0.01 and 0.06 + 0.01 and l_quantity < 25;
\echo m12 q6 date literals run 2
select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.06 - 0.01 and 0.06 + 0.01 and l_quantity < 25;
\echo m12 q6 date literals run 3
select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.06 - 0.01 and 0.06 + 0.01 and l_quantity < 25;
\echo m14 sum(expr) all rows run 1
select sum(l_extendedprice * l_discount) from lineitem;
\echo m14 sum(expr) all rows run 2
select sum(l_extendedprice * l_discount) from lineitem;
\echo m14 sum(expr) all rows run 3
select sum(l_extendedprice * l_discount) from lineitem;
\echo m15 last field compare run 1
select count(*) from lineitem where l_comment = 'x';
\echo m15 last field compare run 2
select count(*) from lineitem where l_comment = 'x';
\echo m15 last field compare run 3
select count(*) from lineitem where l_comment = 'x';
\echo m16 four cheap predicates all true run 1
select count(*) from lineitem where l_orderkey > 0 and l_partkey > 0 and l_suppkey > 0 and l_linenumber > 0;
\echo m16 four cheap predicates all true run 2
select count(*) from lineitem where l_orderkey > 0 and l_partkey > 0 and l_suppkey > 0 and l_linenumber > 0;
\echo m16 four cheap predicates all true run 3
select count(*) from lineitem where l_orderkey > 0 and l_partkey > 0 and l_suppkey > 0 and l_linenumber > 0;
\timing off
\echo explain m01 count(*) no data
explain (analyze, buffers) select count(*) from lineitem;
\echo explain m11 q6 all literals
explain (analyze, buffers) select sum(l_extendedprice * l_discount) from lineitem where l_shipdate >= date '1997-01-01' and l_shipdate < date '1998-01-01' and l_discount between 0.05 and 0.07 and l_quantity < 25;
