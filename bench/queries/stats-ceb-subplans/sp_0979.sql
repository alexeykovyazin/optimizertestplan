SELECT COUNT(*) FROM votes as v, posts as p WHERE p.Id = v.PostId AND v.CreationDate<=CAST('2014-09-10 00:00:00' AS TIMESTAMP) AND p.Score<=32 AND p.ViewCount<=4146
