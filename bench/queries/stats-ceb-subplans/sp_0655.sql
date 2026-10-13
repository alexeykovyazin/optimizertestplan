SELECT COUNT(*) FROM votes as v, comments as c, postLinks as pl, posts as p WHERE p.Id = v.PostId AND p.Id = pl.RelatedPostId AND p.Id = c.PostId
