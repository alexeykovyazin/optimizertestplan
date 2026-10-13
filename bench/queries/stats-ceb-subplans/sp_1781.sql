SELECT COUNT(*) FROM posts as p, postHistory as ph, users as u WHERE p.OwnerUserId = u.Id AND ph.UserId = u.Id AND p.Score>=0 AND ph.CreationDate>=CAST('2010-07-19 19:52:31' AS TIMESTAMP)
