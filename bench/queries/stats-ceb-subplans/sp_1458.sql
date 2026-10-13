SELECT COUNT(*) FROM users as u, votes as v WHERE v.UserId = u.Id AND u.CreationDate>=CAST('2010-12-15 06:00:24' AS TIMESTAMP)
