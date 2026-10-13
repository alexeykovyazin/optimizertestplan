SELECT COUNT(*) FROM users as u, comments as c WHERE c.UserId = u.Id AND c.CreationDate>=CAST('2010-08-01 19:11:47' AS TIMESTAMP) AND c.CreationDate<=CAST('2014-09-11 13:42:51' AS TIMESTAMP)
