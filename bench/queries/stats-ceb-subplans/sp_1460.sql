SELECT COUNT(*) FROM users as u, votes as v, posts as p WHERE p.OwnerUserId = u.Id AND v.UserId = u.Id AND u.CreationDate>=CAST('2010-12-15 06:00:24' AS TIMESTAMP) AND p.CommentCount>=0
