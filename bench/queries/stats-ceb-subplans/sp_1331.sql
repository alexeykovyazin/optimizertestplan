SELECT COUNT(*) FROM badges as b, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=12 AND p.FavoriteCount>=0
