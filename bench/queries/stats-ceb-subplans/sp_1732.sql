SELECT COUNT(*) FROM postHistory as ph, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = ph.UserId AND c.CreationDate<=CAST('2014-08-28 00:18:24' AS TIMESTAMP)
