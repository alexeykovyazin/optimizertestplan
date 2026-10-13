SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND u.UpVotes>=0
