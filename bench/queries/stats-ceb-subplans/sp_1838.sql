SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE u.Id = b.UserId AND u.Id = ph.UserId AND b."Date"<=CAST('2014-09-03 16:13:12' AS TIMESTAMP) AND ph.PostHistoryTypeId=1
