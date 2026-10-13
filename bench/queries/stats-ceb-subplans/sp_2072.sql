SELECT COUNT(*) FROM badges as b, comments as c, postHistory as ph, users as u WHERE u.Id = c.UserId AND u.Id = b.UserId AND u.Id = ph.UserId AND c.Score=0
