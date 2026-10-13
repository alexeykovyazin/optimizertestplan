SELECT COUNT(*) FROM votes as v, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = v.UserId AND v.CreationDate<=CAST('2014-09-11 00:00:00' AS TIMESTAMP)
