SELECT COUNT(*) FROM badges as b, votes as v, users as u WHERE v.UserId = u.Id AND b.UserId = u.Id AND v.BountyAmount>=0 AND v.BountyAmount<=50
