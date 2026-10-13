SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND p.Score<=67 AND c.Score=0
