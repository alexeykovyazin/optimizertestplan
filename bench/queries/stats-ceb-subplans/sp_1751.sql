SELECT COUNT(*) FROM users as u, comments as c, badges as b WHERE u.Id = c.UserId AND u.Id = b.UserId AND u.Reputation>=1 AND u.Reputation<=1183 AND u.Views>=0 AND c.Score=2
