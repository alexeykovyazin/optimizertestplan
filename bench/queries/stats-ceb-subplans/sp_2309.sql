SELECT COUNT(*) FROM users as u, comments as c, votes as v, badges as b, posts as p WHERE p.Id = c.PostId AND c.UserId = u.Id AND b.UserId = u.Id AND p.Id = v.PostId
