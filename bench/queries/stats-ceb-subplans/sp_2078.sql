SELECT COUNT(*) FROM users as u, postHistory as ph, badges as b WHERE u.Id = b.UserId AND u.Id = ph.UserId
