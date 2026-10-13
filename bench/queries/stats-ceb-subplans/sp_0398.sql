SELECT COUNT(*) FROM users as u, badges as b WHERE b.UserId = u.Id AND u.Reputation>=1 AND u.Reputation<=113 AND u.Views>=0 AND u.Views<=51
