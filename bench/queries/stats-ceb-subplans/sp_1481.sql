SELECT COUNT(*) FROM posts as p, postHistory as ph, votes as v WHERE v.PostId = p.Id AND ph.PostId = p.Id AND ph.CreationDate<=CAST('2014-09-05 06:39:25' AS TIMESTAMP) AND v.VoteTypeId=2
