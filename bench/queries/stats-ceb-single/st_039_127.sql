SELECT COUNT(*) FROM posts as p WHERE p.Score>=-1 AND p.CommentCount<=8 AND p.CreationDate>=CAST('2010-07-21 12:30:43' AS TIMESTAMP) AND p.CreationDate<=CAST('2014-09-07 01:11:03' AS TIMESTAMP)
