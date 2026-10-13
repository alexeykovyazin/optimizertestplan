SELECT COUNT(*) FROM users as u WHERE u.DownVotes<=2 AND u.UpVotes>=0 AND u.CreationDate>=CAST('2010-11-26 03:34:11' AS TIMESTAMP)
