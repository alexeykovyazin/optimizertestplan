SELECT COUNT(*) FROM posts as p WHERE p.AnswerCount>=0 AND p.AnswerCount<=9 AND p.CreationDate>=CAST('2010-07-20 18:17:25' AS TIMESTAMP) AND p.CreationDate<=CAST('2014-08-26 12:57:22' AS TIMESTAMP)
