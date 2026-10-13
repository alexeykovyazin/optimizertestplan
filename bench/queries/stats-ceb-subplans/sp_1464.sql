SELECT COUNT(*) FROM votes as v, postHistory as ph, posts as p WHERE v.PostId = p.Id AND ph.PostId = p.Id AND v.CreationDate<=CAST('2014-09-12 00:00:00' AS TIMESTAMP)
