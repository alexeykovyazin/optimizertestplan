SELECT COUNT(*) FROM postHistory as ph, postLinks as pl, posts as p WHERE p.Id = pl.PostId AND p.Id = ph.PostId AND pl.LinkTypeId=1 AND pl.CreationDate>=CAST('2011-10-06 21:41:26' AS TIMESTAMP)
