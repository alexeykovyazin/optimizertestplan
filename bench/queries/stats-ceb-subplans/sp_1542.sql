SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.Reputation>=1 AND u.DownVotes>=0 AND u.DownVotes<=1
