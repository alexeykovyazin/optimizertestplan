SELECT COUNT(*) FROM votes as v, postHistory as ph, users as u WHERE u.Id = v.UserId AND u.Id = ph.UserId AND v.CreationDate<=CAST('2014-09-10 00:00:00' AS TIMESTAMP)
