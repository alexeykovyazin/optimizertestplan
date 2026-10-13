SELECT COUNT(*) FROM users as u, votes as v WHERE v.UserId = u.Id AND u.UpVotes=0
