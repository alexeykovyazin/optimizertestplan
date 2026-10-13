SELECT COUNT(*) FROM posts as p WHERE p.Score>=0 AND p.Score<=19 AND p.CommentCount<=10 AND p.CreationDate<=CAST('2014-08-28 13:31:33' AS TIMESTAMP)
