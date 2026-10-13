SELECT COUNT(*) FROM users as u, votes as v, badges as b WHERE u.Id = b.UserId AND u.Id = v.UserId
