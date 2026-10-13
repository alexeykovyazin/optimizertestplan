SELECT COUNT(*) FROM votes as v, comments as c, posts as p, users as u WHERE u.Id = c.UserId AND u.Id = p.OwnerUserId AND u.Id = v.UserId AND c.Score=0 AND p.ViewCount>=0
