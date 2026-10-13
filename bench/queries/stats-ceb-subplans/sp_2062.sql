SELECT COUNT(*) FROM users as u, comments as c WHERE u.Id = c.UserId AND c.Score=0
