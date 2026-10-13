SELECT COUNT(*) FROM posts as p, votes as v WHERE v.PostId = p.Id AND v.CreationDate>=CAST('2010-07-20 00:00:00' AS TIMESTAMP)
