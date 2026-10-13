SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.Reputation>=1 AND u.DownVotes>=0 AND v.CreationDate>=CAST('2010-07-27 00:00:00' AS TIMESTAMP)
