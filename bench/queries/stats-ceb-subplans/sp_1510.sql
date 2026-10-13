SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.Reputation<=306 AND u.UpVotes>=0
