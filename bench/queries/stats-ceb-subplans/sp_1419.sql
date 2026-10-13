SELECT COUNT(*) FROM users as u, comments as c WHERE u.Id = c.UserId AND u.CreationDate>=CAST('2010-07-19 20:11:48' AS TIMESTAMP) AND u.CreationDate<=CAST('2014-07-09 20:37:10' AS TIMESTAMP)
