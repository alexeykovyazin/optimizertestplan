SELECT COUNT(*) FROM postLinks as pl, posts as p WHERE p.Id = pl.RelatedPostId AND p.Score>=-1 AND p.ViewCount>=0 AND p.CommentCount<=9
