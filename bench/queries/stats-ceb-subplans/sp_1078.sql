SELECT COUNT(*) FROM votes as v, posts as p, postLinks as pl WHERE p.Id = pl.RelatedPostId AND p.Id = v.PostId AND v.VoteTypeId=5 AND p.CommentCount>=0
