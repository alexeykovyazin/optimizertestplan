SELECT COUNT(*) FROM users as u, badges as b, votes as v WHERE b.UserId = u.Id AND v.UserId = u.Id AND u.UpVotes=0
