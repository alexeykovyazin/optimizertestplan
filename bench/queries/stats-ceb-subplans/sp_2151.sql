SELECT COUNT(*) FROM votes as v, posts as p WHERE p.Id = v.PostId AND v.CreationDate>=CAST('2009-02-02 00:00:00' AS TIMESTAMP) AND p.Score>=-1 AND p.Score<=14
