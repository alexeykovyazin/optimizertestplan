SELECT COUNT(*) FROM users as u, postHistory as ph, votes as v WHERE u.Id = v.UserId AND u.Id = ph.UserId AND u.Views>=0
