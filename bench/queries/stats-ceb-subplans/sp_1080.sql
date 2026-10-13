SELECT COUNT(*) FROM votes as v, postLinks as pl, postHistory as ph, posts as p WHERE p.Id = pl.RelatedPostId AND p.Id = v.PostId AND p.Id = ph.PostId AND v.VoteTypeId=5 AND ph.PostHistoryTypeId=2
