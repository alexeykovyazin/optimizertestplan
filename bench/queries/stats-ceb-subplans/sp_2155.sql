SELECT COUNT(*) FROM users as u, badges as b WHERE u.Id = b.UserId AND u.DownVotes>=0 AND b."Date">=CAST('2010-08-04 08:50:31' AS TIMESTAMP) AND b."Date"<=CAST('2014-09-02 02:51:22' AS TIMESTAMP)
