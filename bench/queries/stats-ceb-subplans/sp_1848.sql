SELECT COUNT(*) FROM users as u, postHistory as ph WHERE u.Id = ph.UserId AND u.Views>=0
