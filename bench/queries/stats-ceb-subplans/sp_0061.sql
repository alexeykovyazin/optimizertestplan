SELECT COUNT(*) FROM users as u, votes as v WHERE v.UserId = u.Id AND u.CreationDate>=CAST('2010-07-22 04:38:06' AS TIMESTAMP) AND u.CreationDate<=CAST('2014-09-08 15:55:02' AS TIMESTAMP)
