SELECT COUNT(*) FROM votes as v, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = v.UserId AND c.CreationDate>=CAST('2010-07-27 12:03:40' AS TIMESTAMP)
