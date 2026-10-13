SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.DownVotes>=0 AND u.DownVotes<=3 AND u.UpVotes>=0 AND u.UpVotes<=71 AND v.CreationDate<=CAST('2014-09-10 00:00:00' AS TIMESTAMP)
