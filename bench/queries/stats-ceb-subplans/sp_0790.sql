SELECT COUNT(*) FROM users as u, comments as c WHERE u.Id = c.UserId AND u.Reputation>=1 AND u.DownVotes>=0 AND c.CreationDate<=CAST('2014-09-11 13:24:22' AS TIMESTAMP)
