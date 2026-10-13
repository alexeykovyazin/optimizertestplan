SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND p.Score<=61 AND p.ViewCount<=3627 AND p.AnswerCount>=0 AND p.AnswerCount<=5 AND p.CommentCount<=8 AND p.FavoriteCount>=0
