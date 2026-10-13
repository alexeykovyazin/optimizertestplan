SELECT COUNT(*) FROM users as u, badges as b WHERE b.UserId = u.Id AND b."Date"<=CAST('2014-08-02 12:24:29' AS TIMESTAMP)
