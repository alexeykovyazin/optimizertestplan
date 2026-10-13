SELECT COUNT(*) FROM votes as v, postHistory as ph, posts as p WHERE v.PostId = p.Id AND ph.PostId = p.Id
