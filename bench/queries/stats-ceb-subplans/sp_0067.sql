SELECT COUNT(*) FROM users as u, votes as v, badges as b WHERE v.UserId = u.Id AND b.UserId = u.Id AND u.DownVotes>=0 AND u.DownVotes<=0
