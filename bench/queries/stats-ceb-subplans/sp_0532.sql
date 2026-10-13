SELECT COUNT(*) FROM badges as b, posts as p, votes as v, users as u WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND u.Id = v.UserId
