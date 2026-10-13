SELECT COUNT(*) FROM votes as v, posts as p WHERE p.Id = v.PostId AND v.VoteTypeId=2 AND v.CreationDate<=CAST('2014-09-10 00:00:00' AS TIMESTAMP) AND p.AnswerCount<=4 AND p.FavoriteCount>=0
