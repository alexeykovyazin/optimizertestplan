SELECT COUNT(*) FROM users as u, votes as v, posts as p WHERE u.Id = p.OwnerUserId AND p.Id = v.PostId AND u.Reputation>=1 AND p.Score<=22
