SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = b.UserId AND c.Score=2
