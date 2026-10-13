SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.UpVotes=0 AND u.CreationDate<=CAST('2014-09-12 03:25:34' AS TIMESTAMP) AND v.BountyAmount<=100
