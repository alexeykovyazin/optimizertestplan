SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = v.PostId AND c.CreationDate>=CAST('2010-07-26 19:37:03' AS TIMESTAMP)
