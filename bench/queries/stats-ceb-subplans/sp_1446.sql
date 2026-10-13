SELECT COUNT(*) FROM posts as p, postHistory as ph, users as u WHERE p.OwnerUserId = u.Id AND ph.UserId = u.Id AND p.Score>=0 AND ph.CreationDate>=CAST('2010-08-21 05:30:40' AS TIMESTAMP)
