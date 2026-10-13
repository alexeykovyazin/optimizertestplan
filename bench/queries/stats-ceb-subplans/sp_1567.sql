SELECT COUNT(*) FROM users as u, votes as v WHERE v.UserId = u.Id AND u.Views<=433 AND u.DownVotes>=0 AND u.CreationDate<=CAST('2014-09-12 21:37:39' AS TIMESTAMP)
