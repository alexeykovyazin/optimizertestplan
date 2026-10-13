SELECT COUNT(*) FROM badges as b, votes as v, users as u WHERE u.Id = b.UserId AND u.Id = v.UserId AND v.CreationDate>=CAST('2010-07-20 00:00:00' AS TIMESTAMP)
