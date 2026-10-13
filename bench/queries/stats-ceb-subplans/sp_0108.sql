SELECT COUNT(*) FROM users as u, posts as p, badges as b WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND u.Reputation>=1 AND p.Score<=22
