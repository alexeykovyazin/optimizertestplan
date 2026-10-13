SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE c.UserId = u.Id AND b.UserId = u.Id AND c.CreationDate>=CAST('2010-07-22 01:19:43' AS TIMESTAMP)
