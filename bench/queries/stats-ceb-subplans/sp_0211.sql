SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND b."Date"<=CAST('2014-09-04 08:54:56' AS TIMESTAMP)
