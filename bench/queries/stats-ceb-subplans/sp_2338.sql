SELECT COUNT(*) FROM users as u, comments as c WHERE c.UserId = u.Id AND c.Score=0 AND c.CreationDate>=CAST('2010-07-26 17:09:48' AS TIMESTAMP)
