SELECT COUNT(*) FROM votes as v, posts as p WHERE p.Id = v.PostId AND v.CreationDate>=CAST('2010-07-19 00:00:00' AS TIMESTAMP) AND p.Score<=21 AND p.AnswerCount<=3 AND p.FavoriteCount>=0
