SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=12 AND p.FavoriteCount>=0
