SELECT COUNT(*) FROM votes as v, comments as c, users as u WHERE c.UserId = u.Id AND v.UserId = u.Id AND c.CreationDate>=CAST('2010-07-20 21:37:31' AS TIMESTAMP)
