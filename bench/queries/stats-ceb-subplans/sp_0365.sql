SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE c.UserId = u.Id AND b.UserId = u.Id AND b."Date"<=CAST('2014-08-25 19:05:46' AS TIMESTAMP) AND c.Score=1
