SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE b.UserId = u.Id AND ph.UserId = u.Id AND u.CreationDate<=CAST('2014-09-12 22:21:49' AS TIMESTAMP)
