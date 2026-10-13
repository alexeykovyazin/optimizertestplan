SELECT COUNT(*) FROM badges as b, comments as c, users as u WHERE u.Id = c.UserId AND u.Id = b.UserId AND b."Date"<=CAST('2014-09-02 23:33:16' AS TIMESTAMP)
