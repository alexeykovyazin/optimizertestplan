SELECT COUNT(*) FROM users as u, comments as c, badges as b WHERE c.UserId = u.Id AND b.UserId = u.Id AND u.UpVotes=0 AND c.CreationDate>=CAST('2010-07-20 21:37:31' AS TIMESTAMP)
