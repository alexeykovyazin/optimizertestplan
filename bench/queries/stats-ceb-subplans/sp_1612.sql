SELECT COUNT(*) FROM posts as p, postLinks as pl WHERE pl.PostId = p.Id AND pl.CreationDate>=CAST('2011-11-21 22:39:41' AS TIMESTAMP) AND pl.CreationDate<=CAST('2014-09-01 16:29:56' AS TIMESTAMP)
