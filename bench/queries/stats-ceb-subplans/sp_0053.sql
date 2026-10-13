SELECT COUNT(*) FROM users as u, posts as p, postLinks as pl WHERE p.OwnerUserId = u.Id AND p.Id = pl.PostId AND u.CreationDate<=CAST('2014-09-12 07:12:16' AS TIMESTAMP) AND p.CommentCount<=17
