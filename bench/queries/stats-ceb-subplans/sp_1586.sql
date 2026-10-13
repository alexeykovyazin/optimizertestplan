SELECT COUNT(*) FROM users as u, comments as c WHERE u.Id = c.UserId AND u.Reputation>=1 AND c.Score=1 AND c.CreationDate>=CAST('2010-08-27 14:12:07' AS TIMESTAMP)
