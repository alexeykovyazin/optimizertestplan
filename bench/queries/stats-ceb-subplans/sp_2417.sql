SELECT COUNT(*) FROM postHistory as ph, postLinks as pl, posts as p WHERE p.Id = pl.RelatedPostId AND p.Id = ph.PostId AND pl.LinkTypeId=1
