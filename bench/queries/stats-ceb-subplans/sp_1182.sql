SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND p.PostTypeId=1 AND p.Score<=192 AND p.ViewCount>=0 AND p.ViewCount<=2772 AND p.AnswerCount<=5
