SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.CreationDate>=CAST('2010-07-20 01:27:29' AS TIMESTAMP)
