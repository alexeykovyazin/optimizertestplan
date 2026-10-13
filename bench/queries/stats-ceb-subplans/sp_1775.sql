SELECT COUNT(*) FROM badges as b, users as u WHERE b.UserId = u.Id AND b."Date">=CAST('2010-07-20 10:34:10' AS TIMESTAMP) AND u.Reputation>=1 AND u.Reputation<=750
