SELECT COUNT(*) FROM posts as p, comments as c, postHistory as ph WHERE c.PostId = p.Id AND ph.PostId = p.Id AND ph.CreationDate<=CAST('2014-06-18 17:14:07' AS TIMESTAMP)
