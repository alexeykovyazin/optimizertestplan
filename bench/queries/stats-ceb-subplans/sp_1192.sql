SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = v.PostId AND p.Id = c.PostId AND p.PostTypeId=1 AND p.Score<=192 AND p.ViewCount>=0 AND p.ViewCount<=2772 AND p.AnswerCount<=5
