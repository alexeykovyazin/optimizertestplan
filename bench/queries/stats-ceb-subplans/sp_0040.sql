SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE c.UserId = u.Id AND b.UserId = u.Id AND b."Date">=CAST('2010-07-19 20:54:06' AS TIMESTAMP) AND c.Score=0
