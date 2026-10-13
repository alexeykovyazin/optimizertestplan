SELECT COUNT(*) FROM votes as v, posts as p WHERE p.Id = v.PostId AND v.VoteTypeId=5 AND p.ViewCount>=0 AND p.AnswerCount>=0 AND p.AnswerCount<=7 AND p.FavoriteCount>=0 AND p.FavoriteCount<=17
