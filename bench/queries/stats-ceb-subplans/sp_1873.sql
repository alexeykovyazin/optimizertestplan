SELECT COUNT(*) FROM votes as v, comments as c, postHistory as ph, posts as p WHERE p.Id = c.PostId AND p.Id = v.PostId AND p.Id = ph.PostId AND v.VoteTypeId=2 AND c.Score=0
