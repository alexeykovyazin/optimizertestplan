SELECT COUNT(*) FROM postLinks as pl, posts as p WHERE p.Id = pl.RelatedPostId AND pl.CreationDate<=CAST('2014-06-25 13:05:06' AS TIMESTAMP) AND p.Score>=-1 AND p.Score<=14
