SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE c.UserId = u.Id AND b.UserId = u.Id AND b."Date"<=CAST('2014-08-20 12:16:56' AS TIMESTAMP) AND c.Score=0
