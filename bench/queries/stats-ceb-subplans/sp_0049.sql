SELECT COUNT(*) FROM postHistory as ph, postLinks as pl, posts as p WHERE pl.PostId = p.Id AND ph.PostId = p.Id AND ph.CreationDate>=CAST('2010-07-20 00:30:00' AS TIMESTAMP)
