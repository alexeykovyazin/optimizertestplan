SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND c.CreationDate>=CAST('2010-07-21 11:05:37' AS TIMESTAMP) AND c.CreationDate<=CAST('2014-08-25 17:59:25' AS TIMESTAMP)
