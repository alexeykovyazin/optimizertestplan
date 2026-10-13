SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE ph.PostId = p.Id AND ph.CreationDate>=CAST('2010-08-06 03:14:53' AS TIMESTAMP) AND p.CommentCount>=0 AND p.CommentCount<=14
