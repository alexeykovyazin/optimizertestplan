SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.CreationDate>=CAST('2010-11-16 06:03:04' AS TIMESTAMP) AND v.CreationDate<=CAST('2014-09-06 00:00:00' AS TIMESTAMP)
