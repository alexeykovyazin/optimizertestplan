SELECT COUNT(*) FROM votes as v, postLinks as pl, posts as p WHERE p.Id = pl.PostId AND p.Id = v.PostId AND pl.CreationDate<=CAST('2014-08-05 18:27:51' AS TIMESTAMP)
