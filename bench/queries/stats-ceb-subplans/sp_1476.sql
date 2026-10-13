SELECT COUNT(*) FROM posts as p, postHistory as ph WHERE ph.PostId = p.Id AND ph.CreationDate<=CAST('2014-09-05 06:39:25' AS TIMESTAMP)
