SELECT COUNT(*) FROM users as u, comments as c WHERE c.UserId = u.Id AND u.UpVotes>=0 AND c.Score=0 AND c.CreationDate>=CAST('2010-07-24 06:46:49' AS TIMESTAMP)
