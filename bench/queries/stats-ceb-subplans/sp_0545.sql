SELECT COUNT(*) FROM badges as b, votes as v, users as u WHERE u.Id = b.UserId AND u.Id = v.UserId AND b."Date"<=CAST('2014-09-12 12:56:22' AS TIMESTAMP) AND v.BountyAmount>=0 AND v.BountyAmount<=200
