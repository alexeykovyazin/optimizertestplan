SELECT COUNT(*) FROM posts as p, postHistory as ph, users as u WHERE p.OwnerUserId = u.Id AND ph.UserId = u.Id AND p.FavoriteCount<=5 AND ph.CreationDate>=CAST('2011-05-20 18:43:03' AS TIMESTAMP)
