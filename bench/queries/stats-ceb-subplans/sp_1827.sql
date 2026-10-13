SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE u.Id = b.UserId AND u.Id = ph.UserId AND b."Date">=CAST('2010-07-19 21:54:06' AS TIMESTAMP)
