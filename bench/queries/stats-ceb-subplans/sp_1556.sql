SELECT COUNT(*) FROM users as u, votes as v WHERE v.UserId = u.Id AND u.DownVotes<=0 AND u.UpVotes>=0 AND u.UpVotes<=72
