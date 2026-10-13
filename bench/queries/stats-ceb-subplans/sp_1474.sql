SELECT COUNT(*) FROM posts as p, comments as c WHERE c.PostId = p.Id AND c.Score=0 AND c.CreationDate>=CAST('2010-08-26 06:55:11' AS TIMESTAMP)
