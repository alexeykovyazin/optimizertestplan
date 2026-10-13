SELECT COUNT(*) FROM users as u, comments as c WHERE u.Id = c.UserId AND u.Views>=0 AND u.Views<=74 AND c.Score=0
