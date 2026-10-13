SELECT COUNT(*) FROM users as u, comments as c WHERE c.UserId = u.Id AND c.CreationDate>=CAST('2010-08-05 00:36:02' AS TIMESTAMP) AND c.CreationDate<=CAST('2014-09-08 16:50:49' AS TIMESTAMP)
