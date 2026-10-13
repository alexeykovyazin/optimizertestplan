SELECT COUNT(*) FROM users as u, posts as p, badges as b WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=12 AND p.FavoriteCount>=0
