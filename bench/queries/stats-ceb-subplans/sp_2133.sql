SELECT COUNT(*) FROM badges as b, users as u WHERE u.Id = b.UserId AND b."Date"<=CAST('2014-09-06 17:33:22' AS TIMESTAMP) AND u.Reputation>=1
