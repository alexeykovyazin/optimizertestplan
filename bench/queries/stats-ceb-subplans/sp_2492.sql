SELECT COUNT(*) FROM postHistory as ph, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = ph.PostId AND p.AnswerCount>=0 AND p.CommentCount>=0
