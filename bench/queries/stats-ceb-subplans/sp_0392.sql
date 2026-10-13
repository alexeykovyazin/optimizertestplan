SELECT COUNT(*) FROM users as u, comments as c WHERE c.UserId = u.Id AND u.Reputation>=1 AND u.Reputation<=113 AND u.Views>=0 AND u.Views<=51 AND c.Score=1
