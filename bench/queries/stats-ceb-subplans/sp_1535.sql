SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND b."Date"<=CAST('2014-09-11 07:27:36' AS TIMESTAMP)
