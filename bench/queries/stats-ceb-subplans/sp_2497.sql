SELECT COUNT(*) FROM votes as v, posts as p, postHistory as ph WHERE p.Id = v.PostId AND p.Id = ph.PostId AND p.AnswerCount>=0 AND p.CommentCount>=0
