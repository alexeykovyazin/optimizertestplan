SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND u.DownVotes<=0 AND u.UpVotes<=47
