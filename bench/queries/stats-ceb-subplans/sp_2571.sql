SELECT COUNT(*) FROM votes as v, postHistory as ph, posts as p WHERE p.Id = v.PostId AND p.Id = ph.PostId AND ph.CreationDate>=CAST('2010-11-27 03:38:45' AS TIMESTAMP)
