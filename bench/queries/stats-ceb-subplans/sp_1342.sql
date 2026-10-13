SELECT COUNT(*) FROM users as u, posts as p, postHistory as ph WHERE u.Id = p.OwnerUserId AND p.Id = ph.PostId AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=12 AND p.FavoriteCount>=0
