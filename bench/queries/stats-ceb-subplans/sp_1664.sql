SELECT COUNT(*) FROM posts as p, postLinks as pl WHERE pl.PostId = p.Id AND pl.LinkTypeId=1 AND pl.CreationDate>=CAST('2010-10-19 15:02:42' AS TIMESTAMP)
