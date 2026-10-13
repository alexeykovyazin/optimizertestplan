SELECT COUNT(*) FROM votes as v, comments as c, users as u WHERE c.UserId = u.Id AND v.UserId = u.Id AND v.BountyAmount<=50 AND c.Score=1
