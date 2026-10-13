SELECT COUNT(*) FROM users as u, comments as c, badges as b WHERE u.Id = c.UserId AND u.Id = b.UserId AND u.UpVotes>=0 AND u.UpVotes<=18 AND c.Score=0
