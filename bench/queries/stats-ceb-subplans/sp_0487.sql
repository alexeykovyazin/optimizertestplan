SELECT COUNT(*) FROM users as u, posts as p WHERE u.Id = p.OwnerUserId AND u.CreationDate>=CAST('2011-02-08 18:11:37' AS TIMESTAMP) AND p.Score=1 AND p.ViewCount>=0 AND p.FavoriteCount>=0
