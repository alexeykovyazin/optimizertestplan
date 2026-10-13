SELECT COUNT(*) FROM votes as v, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = v.UserId AND c.Score=1 AND c.CreationDate>=CAST('2010-07-20 23:17:28' AS TIMESTAMP)
