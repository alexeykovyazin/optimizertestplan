SELECT COUNT(*) FROM badges as b, users as u WHERE b.UserId = u.Id AND u.CreationDate<=CAST('2014-09-12 22:21:49' AS TIMESTAMP)
