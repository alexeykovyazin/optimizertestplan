SELECT COUNT(*) FROM users as u, comments as c, votes as v, posts as p WHERE u.Id = c.UserId AND c.PostId = p.Id AND v.PostId = p.Id AND u.Views>=0 AND u.Views<=74 AND c.Score=0
