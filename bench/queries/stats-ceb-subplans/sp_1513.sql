SELECT COUNT(*) FROM users as u, comments as c, votes as v WHERE u.Id = c.UserId AND u.Id = v.UserId AND u.Reputation<=306 AND u.UpVotes>=0 AND c.Score=0
