SELECT COUNT(*) FROM votes as v, comments as c, posts as p WHERE p.Id = c.PostId AND p.Id = v.PostId AND v.CreationDate>=CAST('2009-02-02 00:00:00' AS TIMESTAMP)
