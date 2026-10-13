SELECT COUNT(*) FROM users as u, comments as c, postHistory as ph, votes as v, posts as p WHERE p.Id = c.PostId AND c.UserId = u.Id AND p.Id = v.PostId AND p.Id = ph.PostId
