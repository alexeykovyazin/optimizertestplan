SELECT COUNT(*) FROM badges as b, comments as c, postHistory as ph, users as u WHERE c.UserId = u.Id AND ph.UserId = u.Id AND b.UserId = u.Id AND b."Date">=CAST('2010-09-26 12:17:14' AS TIMESTAMP)
