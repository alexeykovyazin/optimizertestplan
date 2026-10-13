SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = v.PostId AND p.AnswerCount>=0 AND p.CommentCount>=0
