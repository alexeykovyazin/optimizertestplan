SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE c.PostId = p.Id AND v.PostId = p.Id AND v.VoteTypeId=2 AND c.Score=0 AND c.CreationDate>=CAST('2010-08-26 06:55:11' AS TIMESTAMP)
