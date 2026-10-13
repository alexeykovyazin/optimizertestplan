SELECT COUNT(*) FROM users as u, posts as p WHERE u.Id = p.OwnerUserId AND p.AnswerCount>=0 AND p.AnswerCount<=7 AND p.CreationDate<=CAST('2014-09-12 00:03:32' AS TIMESTAMP)
