SELECT COUNT(*) FROM posts as p, comments as c, votes as v WHERE c.PostId = p.Id AND v.PostId = p.Id AND v.CreationDate>=CAST('2010-07-20 00:00:00' AS TIMESTAMP)
