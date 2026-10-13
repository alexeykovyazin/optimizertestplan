SELECT COUNT(*) FROM votes as v, postHistory as ph, posts as p WHERE p.Id = v.PostId AND p.Id = ph.PostId AND v.VoteTypeId=2 AND v.CreationDate>=CAST('2010-07-27 00:00:00' AS TIMESTAMP)
