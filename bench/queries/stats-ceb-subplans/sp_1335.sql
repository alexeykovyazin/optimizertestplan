SELECT COUNT(*) FROM postHistory as ph, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = ph.PostId AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=12 AND p.FavoriteCount>=0
