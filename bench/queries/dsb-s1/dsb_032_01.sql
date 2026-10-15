select FIRST 100  sum(cs_ext_discount_amt)  as "excess discount amount"
from
   catalog_sales
   ,item
   ,date_dim
where
(i_manufact_id in (214, 376, 518, 755, 996)
or i_manager_id BETWEEN 71 and 100)
and i_item_sk = cs_item_sk
and d_date between '2000-03-06' and
        DATEADD(90 DAY TO CAST('2000-03-06' AS DATE))
and d_date_sk = cs_sold_date_sk
and cs_ext_discount_amt
     > (
         select
            1.3 * avg(cs_ext_discount_amt)
         from
            catalog_sales
           ,date_dim
         where
              cs_item_sk = i_item_sk
          and d_date between '2000-03-06' and
                             DATEADD(90 DAY TO CAST('2000-03-06' AS DATE))
          and d_date_sk = cs_sold_date_sk
          and cs_list_price between 80 and 109
          and cs_sales_price / cs_list_price BETWEEN 80 * 0.01 AND 100 * 0.01
      )
order by sum(cs_ext_discount_amt)
