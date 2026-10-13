SELECT COUNT(*) FROM badges as b, comments as c, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND p.Id = c.PostId
