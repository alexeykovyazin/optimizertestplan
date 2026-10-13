SELECT COUNT(*) FROM postHistory as ph, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = ph.UserId AND ph.CreationDate<=CAST('2014-08-18 08:54:12' AS TIMESTAMP) AND c.Score=0
