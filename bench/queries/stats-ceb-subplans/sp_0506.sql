SELECT COUNT(*) FROM badges as b, users as u WHERE u.Id = b.UserId AND b."Date"<=CAST('2014-08-22 02:21:55' AS TIMESTAMP) AND u.DownVotes<=0
