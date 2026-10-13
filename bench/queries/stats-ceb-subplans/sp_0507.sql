SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE u.Id = b.UserId AND u.Id = ph.UserId AND b."Date"<=CAST('2014-08-22 02:21:55' AS TIMESTAMP)
