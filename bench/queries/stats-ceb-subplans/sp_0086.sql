SELECT COUNT(*) FROM users as u, posts as p WHERE p.OwnerUserId = u.Id AND u.UpVotes>=0 AND u.CreationDate>=CAST('2010-08-21 21:27:38' AS TIMESTAMP)
