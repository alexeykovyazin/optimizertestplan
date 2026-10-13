SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE c.UserId = u.Id AND b.UserId = u.Id AND c.CreationDate>=CAST('2010-07-20 21:37:31' AS TIMESTAMP)
