SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND p.ViewCount>=0 AND p.AnswerCount<=5 AND p.CommentCount<=12 AND p.FavoriteCount>=0 AND c.Score=0
