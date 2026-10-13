SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = b.UserId AND c.Score=1 AND c.CreationDate>=CAST('2010-07-20 23:17:28' AS TIMESTAMP)
