SELECT COUNT(*) FROM posts as p WHERE p.AnswerCount>=0 AND p.AnswerCount<=7 AND p.CreationDate<=CAST('2014-09-12 00:03:32' AS TIMESTAMP)
