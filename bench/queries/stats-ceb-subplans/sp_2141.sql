SELECT COUNT(*) FROM badges as b, users as u, votes as v WHERE u.Id = b.UserId AND u.Id = v.UserId AND b."Date"<=CAST('2014-09-06 17:33:22' AS TIMESTAMP) AND u.Reputation>=1
