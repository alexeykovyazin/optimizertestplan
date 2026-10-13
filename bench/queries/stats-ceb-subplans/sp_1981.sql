SELECT COUNT(*) FROM posts as p, comments as c, users as u WHERE p.OwnerUserId = u.Id AND c.UserId = u.Id AND p.ViewCount>=0 AND p.AnswerCount>=0 AND p.AnswerCount<=5
