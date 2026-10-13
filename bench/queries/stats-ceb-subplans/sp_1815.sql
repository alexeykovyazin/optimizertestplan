SELECT COUNT(*) FROM users as u, postHistory as ph WHERE ph.UserId = u.Id AND u.CreationDate<=CAST('2014-09-12 22:21:49' AS TIMESTAMP)
