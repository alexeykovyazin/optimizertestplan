SELECT COUNT(*) FROM users as u, comments as c, postHistory as ph, badges as b WHERE u.Id = c.UserId AND u.Id = b.UserId AND u.Id = ph.UserId AND c.Score=0
