SELECT COUNT(*) FROM users as u, comments as c WHERE u.Id = c.UserId AND u.Reputation<=306 AND u.UpVotes>=0 AND c.Score=0
