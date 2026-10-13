SELECT COUNT(*) FROM badges as b, users as u WHERE u.Id = b.UserId AND b."Date">=CAST('2010-07-19 21:54:06' AS TIMESTAMP) AND u.DownVotes>=0 AND u.DownVotes<=3 AND u.UpVotes>=0 AND u.UpVotes<=71
