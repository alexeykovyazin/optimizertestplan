SELECT COUNT(*) FROM posts as p, postLinks as pl, postHistory as ph WHERE pl.PostId = p.Id AND ph.PostId = p.Id AND pl.LinkTypeId=1 AND pl.CreationDate>=CAST('2011-06-14 13:31:35' AS TIMESTAMP)
