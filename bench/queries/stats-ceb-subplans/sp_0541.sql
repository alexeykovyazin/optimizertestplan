SELECT COUNT(*) FROM votes as v, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = v.UserId AND v.BountyAmount>=0 AND v.BountyAmount<=200
