SELECT COUNT(*) FROM posts as p, comments as c WHERE p.Id = c.PostId AND p.Score>=-1 AND p.ViewCount>=0 AND p.CommentCount<=9 AND c.CreationDate>=CAST('2010-07-22 01:19:43' AS TIMESTAMP)
