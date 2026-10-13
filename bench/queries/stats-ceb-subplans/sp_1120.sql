SELECT COUNT(*) FROM votes as v, posts as p, postLinks as pl WHERE p.Id = pl.RelatedPostId AND p.Id = v.PostId AND p.Score<=67
