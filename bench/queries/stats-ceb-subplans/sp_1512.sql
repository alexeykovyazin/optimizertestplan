SELECT COUNT(*) FROM users as u, comments as c, posts as p WHERE u.Id = c.UserId AND u.Id = p.OwnerUserId AND u.Reputation<=306 AND u.UpVotes>=0 AND c.Score=0 AND p.ViewCount>=0
