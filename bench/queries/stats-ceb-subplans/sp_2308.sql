SELECT COUNT(*) FROM users as u, comments as c, postHistory as ph, badges as b, posts as p WHERE c.UserId = u.Id AND b.UserId = u.Id AND p.Id = c.PostId AND p.Id = ph.PostId
