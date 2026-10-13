SELECT COUNT(*) FROM postLinks as pl, comments as c, posts as p WHERE pl.PostId = p.Id AND c.PostId = p.Id AND pl.LinkTypeId=1 AND pl.CreationDate>=CAST('2010-10-19 15:02:42' AS TIMESTAMP)
