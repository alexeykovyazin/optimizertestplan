SELECT COUNT(*) FROM users as u, comments as c, badges as b WHERE u.Id = c.UserId AND u.Id = b.UserId AND u.DownVotes<=0 AND u.UpVotes<=47 AND c.CreationDate<=CAST('2014-09-10 00:33:30' AS TIMESTAMP)
