SELECT COUNT(*) FROM users as u, comments as c WHERE c.UserId = u.Id AND c.Score=0
