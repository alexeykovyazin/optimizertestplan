SELECT COUNT(*) FROM users as u, badges as b WHERE b.UserId = u.Id AND u.UpVotes>=0 AND b."Date">=CAST('2010-07-19 20:34:06' AS TIMESTAMP) AND b."Date"<=CAST('2014-09-12 15:11:36' AS TIMESTAMP)
