SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = v.PostId AND v.VoteTypeId=2 AND c.CreationDate<=CAST('2014-09-10 02:42:35' AS TIMESTAMP)
