SELECT COUNT(*) FROM posts as p, votes as v WHERE v.PostId = p.Id AND v.CreationDate>=CAST('2010-07-19 00:00:00' AS TIMESTAMP) AND v.CreationDate<=CAST('2014-09-10 00:00:00' AS TIMESTAMP)
