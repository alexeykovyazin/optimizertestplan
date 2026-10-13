SELECT COUNT(*) FROM users as u, votes as v WHERE u.Id = v.UserId AND u.Views=5 AND u.DownVotes>=0 AND u.UpVotes>=0 AND u.UpVotes<=224 AND u.CreationDate<=CAST('2014-09-04 04:41:22' AS TIMESTAMP)
