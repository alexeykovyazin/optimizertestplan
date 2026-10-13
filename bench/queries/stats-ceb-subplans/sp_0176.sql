SELECT COUNT(*) FROM badges as b, votes as v, users as u WHERE u.Id = b.UserId AND u.Id = v.UserId AND v.BountyAmount>=0 AND v.CreationDate<=CAST('2014-09-11 00:00:00' AS TIMESTAMP)
