SELECT COUNT(*) FROM postHistory as ph, comments as c, users as u WHERE c.UserId = u.Id AND ph.UserId = u.Id AND ph.CreationDate<=CAST('2014-09-02 07:58:47' AS TIMESTAMP) AND c.Score=2
