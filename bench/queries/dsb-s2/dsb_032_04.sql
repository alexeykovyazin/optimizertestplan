select FIRST 100  sum(cs_ext_discount_amt)  as "excess discount amount"
from
   catalog_sales
   ,item
   ,date_dim
where
(i_manufact_id in (327, 488, 732, 868, 924)
or i_manager_id BETWEEN 18 and 47)
and i_item_sk = cs_item_sk
and d_date between '2001-03-27' and
        DATEADD(90 DAY TO CAST('2001-03-27' AS DATE))
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
          and d_date between '2001-03-27' and
                             DATEADD(90 DAY TO CAST('2001-03-27' AS DATE))
          and d_date_sk = cs_sold_date_sk
          and cs_list_price between 114 and 143
          and cs_sales_price / cs_list_price BETWEEN 3 * 0.01 AND 23 * 0.01
      )
order by sum(cs_ext_discount_amt)
