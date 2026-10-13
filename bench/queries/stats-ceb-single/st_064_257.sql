SELECT COUNT(*) FROM users as u WHERE u.DownVotes<=0 AND u.UpVotes>=0 AND u.CreationDate>=CAST('2010-09-18 01:58:41' AS TIMESTAMP)
