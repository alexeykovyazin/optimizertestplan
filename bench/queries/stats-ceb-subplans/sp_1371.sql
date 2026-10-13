SELECT COUNT(*) FROM postHistory as ph, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = ph.PostId AND c.Score=0 AND p.Score<=21 AND p.AnswerCount<=3 AND p.FavoriteCount>=0
