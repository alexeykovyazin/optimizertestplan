SELECT COUNT(*) FROM users as u, comments as c, votes as v WHERE c.UserId = u.Id AND v.UserId = u.Id AND u.DownVotes>=0 AND v.BountyAmount<=50
