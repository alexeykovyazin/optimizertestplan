SELECT COUNT(*) FROM badges as b, votes as v, users as u WHERE v.UserId = u.Id AND b.UserId = u.Id AND b."Date"<=CAST('2014-08-25 19:05:46' AS TIMESTAMP) AND v.BountyAmount<=50
