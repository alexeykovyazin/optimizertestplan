SELECT COUNT(*) FROM postLinks as pl, posts as p WHERE p.Id = pl.RelatedPostId AND pl.LinkTypeId=1 AND p.Score<=32 AND p.ViewCount<=4146
