SELECT COUNT(*) FROM postLinks as pl, posts as p WHERE pl.PostId = p.Id AND p.CreationDate>=CAST('2010-07-19 20:08:37' AS TIMESTAMP)
