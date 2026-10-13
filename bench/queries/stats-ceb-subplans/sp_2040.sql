SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE u.Id = b.UserId AND u.Id = ph.UserId AND ph.CreationDate<=CAST('2014-08-18 08:54:12' AS TIMESTAMP)
