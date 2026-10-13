SELECT COUNT(*) FROM posts as p, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = p.OwnerUserId AND p.Score<=52 AND p.AnswerCount>=0
