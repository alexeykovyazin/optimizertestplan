SELECT COUNT(*) FROM posts as p WHERE p.Score>=-2 AND p.CommentCount<=18 AND p.CreationDate>=CAST('2010-07-21 13:50:08' AS TIMESTAMP) AND p.CreationDate<=CAST('2014-09-11 00:53:10' AS TIMESTAMP)
