SELECT COUNT(*) FROM votes as v, comments as c, posts as p, postLinks as pl WHERE p.Id = v.PostId AND p.Id = pl.RelatedPostId AND p.Id = c.PostId AND v.VoteTypeId=5 AND p.CommentCount>=0
