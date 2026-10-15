select
    s_suppkey,
    s_name,
    s_address,
    s_phone,
    total_revenue
from
    supplier,
    (select
    l_suppkey as supplier_no,
    sum(l_extendedprice * (1 - l_discount)) as total_revenue
from
    lineitem
where
    l_shipdate >= CAST('1995-09-01' AS DATE)
    and l_shipdate < DATEADD(3 MONTH TO CAST('1995-09-01' AS DATE))
group by
    l_suppkey) revenue0
where
    s_suppkey = supplier_no
    and total_revenue = (
        select
            max(total_revenue)
        from (select
    l_suppkey as supplier_no,
    sum(l_extendedprice * (1 - l_discount)) as total_revenue
from
    lineitem
where
    l_shipdate >= CAST('1995-09-01' AS DATE)
    and l_shipdate < DATEADD(3 MONTH TO CAST('1995-09-01' AS DATE))
group by
    l_suppkey) revenue0
    )
order by
    s_suppkey
