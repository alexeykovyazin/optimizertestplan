SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = v.PostId AND p.Id = c.PostId AND v.VoteTypeId=15 AND c.CreationDate>=CAST('2010-07-22 01:19:43' AS TIMESTAMP)
