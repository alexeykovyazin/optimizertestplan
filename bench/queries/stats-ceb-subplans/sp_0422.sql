SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE u.Id = b.UserId AND u.Id = ph.UserId AND b."Date">=CAST('2010-10-20 08:33:44' AS TIMESTAMP) AND ph.PostHistoryTypeId=2
