SELECT COUNT(*) FROM postLinks as pl, posts as p WHERE pl.RelatedPostId = p.Id AND pl.LinkTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=14
