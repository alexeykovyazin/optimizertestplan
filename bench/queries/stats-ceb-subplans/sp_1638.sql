SELECT COUNT(*) FROM posts as p, postLinks as pl WHERE pl.PostId = p.Id AND pl.CreationDate>=CAST('2011-03-22 06:18:34' AS TIMESTAMP) AND pl.CreationDate<=CAST('2014-08-22 20:04:25' AS TIMESTAMP)
