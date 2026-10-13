SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND u.CreationDate>=CAST('2010-07-20 01:27:29' AS TIMESTAMP)
