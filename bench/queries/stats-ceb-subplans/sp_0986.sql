SELECT COUNT(*) FROM badges as b, comments as c, posts as p, users as u WHERE c.UserId = u.Id AND b.UserId = u.Id AND p.Id = c.PostId AND c.Score=0 AND p.Score<=32 AND p.ViewCount<=4146
