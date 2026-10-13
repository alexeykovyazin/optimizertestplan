SELECT COUNT(*) FROM votes as v, posts as p, postLinks as pl, postHistory as ph WHERE p.Id = pl.RelatedPostId AND p.Id = v.PostId AND p.Id = ph.PostId AND p.Score<=67 AND ph.PostHistoryTypeId=34
