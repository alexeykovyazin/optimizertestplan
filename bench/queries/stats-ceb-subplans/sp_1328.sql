SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = v.PostId AND p.Id = c.PostId AND v.BountyAmount<=50
