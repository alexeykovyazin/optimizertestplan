SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.Views>=0 AND u.CreationDate>=CAST('2010-07-27 09:38:05' AS TIMESTAMP)
