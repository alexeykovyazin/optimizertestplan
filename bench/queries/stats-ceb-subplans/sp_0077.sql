SELECT COUNT(*) FROM votes as v, postLinks as pl, posts as p WHERE pl.PostId = p.Id AND v.PostId = p.Id AND v.VoteTypeId=2 AND v.CreationDate<=CAST('2014-09-12 00:00:00' AS TIMESTAMP)
