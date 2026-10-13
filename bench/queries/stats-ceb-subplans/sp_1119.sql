SELECT COUNT(*) FROM postHistory as ph, posts as p, postLinks as pl WHERE p.Id = pl.RelatedPostId AND p.Id = ph.PostId AND ph.PostHistoryTypeId=34 AND p.Score<=67
