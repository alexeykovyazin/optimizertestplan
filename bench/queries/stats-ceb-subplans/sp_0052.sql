SELECT COUNT(*) FROM users as u, posts as p WHERE p.OwnerUserId = u.Id AND u.CreationDate<=CAST('2014-09-12 07:12:16' AS TIMESTAMP) AND p.CommentCount<=17
