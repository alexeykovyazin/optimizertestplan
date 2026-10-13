SELECT COUNT(*) FROM users as u, comments as c, badges as b WHERE u.Id = c.UserId AND u.Id = b.UserId AND c.Score=0
