SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND p.AnswerCount>=0 AND p.AnswerCount<=4 AND p.CreationDate<=CAST('2014-09-12 15:56:19' AS TIMESTAMP) AND c.Score=0
