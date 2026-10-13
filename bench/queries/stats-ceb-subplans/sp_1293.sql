SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND p.ViewCount>=0 AND p.AnswerCount>=0 AND p.AnswerCount<=7 AND p.FavoriteCount>=0 AND p.FavoriteCount<=17
