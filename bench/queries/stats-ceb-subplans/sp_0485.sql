SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND p.Score=1 AND p.ViewCount>=0 AND p.FavoriteCount>=0
