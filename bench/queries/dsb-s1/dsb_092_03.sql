select FIRST 100 
   sum(ws_ext_discount_amt)  as "Excess Discount Amount"
from
    web_sales
   ,item
   ,date_dim
where
(i_manufact_id BETWEEN 791 and 990
or i_category IN ('Books', 'Home', 'Shoes'))
and i_item_sk = ws_item_sk
and d_date between '2002-01-22' and
        DATEADD(90 DAY TO CAST('2002-01-22' AS DATE))
and d_date_sk = ws_sold_date_sk
and ws_wholesale_cost BETWEEN 80 AND 100
and ws_ext_discount_amt
     > (
         SELECT
            1.3 * avg(ws_ext_discount_amt)
         FROM
            web_sales
           ,date_dim
         WHERE
              ws_item_sk = i_item_sk
          and d_date between '2002-01-22' and
                             DATEADD(90 DAY TO CAST('2002-01-22' AS DATE))
          and d_date_sk = ws_sold_date_sk
          and ws_wholesale_cost BETWEEN 80 AND 100
          and ws_sales_price / ws_list_price BETWEEN 40 * 0.01 AND 55 * 0.01
  )
order by sum(ws_ext_discount_amt)
