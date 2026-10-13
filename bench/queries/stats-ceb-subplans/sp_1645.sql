SELECT COUNT(*) FROM votes as v, comments as c, postHistory as ph, posts as p WHERE c.PostId = p.Id AND ph.PostId = p.Id AND v.PostId = p.Id AND c.Score=0
