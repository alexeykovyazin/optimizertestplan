SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND u.Reputation>=1 AND b."Date"<=CAST('2014-08-19 10:32:13' AS TIMESTAMP)
