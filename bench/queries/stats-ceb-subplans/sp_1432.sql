SELECT COUNT(*) FROM users as u, badges as b WHERE b.UserId = u.Id AND u.Views>=0 AND u.DownVotes>=0 AND u.DownVotes<=2
