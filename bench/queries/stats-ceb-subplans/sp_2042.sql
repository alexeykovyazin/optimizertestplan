SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND u.Views=0 AND u.DownVotes>=0 AND u.DownVotes<=60
