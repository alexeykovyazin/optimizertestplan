SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND p.Score<=21 AND p.AnswerCount<=3 AND p.FavoriteCount>=0
