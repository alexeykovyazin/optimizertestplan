SELECT COUNT(*) FROM postLinks as pl, comments as c, posts as p WHERE p.Id = pl.RelatedPostId AND p.Id = c.PostId AND c.CreationDate>=CAST('2010-07-22 01:19:43' AS TIMESTAMP)
