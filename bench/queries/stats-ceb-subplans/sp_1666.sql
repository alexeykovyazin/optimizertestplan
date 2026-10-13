SELECT COUNT(*) FROM posts as p, postHistory as ph WHERE ph.PostId = p.Id AND ph.CreationDate<=CAST('2014-06-18 17:14:07' AS TIMESTAMP)
