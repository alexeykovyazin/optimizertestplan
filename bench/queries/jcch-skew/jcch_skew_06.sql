-- using 42 as a seed to the RNG


select
	sum(l_extendedprice * l_discount) as revenue
from
	lineitem
where
	l_shipdate >= CAST('1994-01-01' AS DATE)
	and l_shipdate < DATEADD(1 YEAR TO CAST('1994-01-01' AS DATE))
	and l_discount between 0.06 - 0.01 and 0.06 + 0.01
	and l_quantity < 100
