SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE b.UserId = u.Id AND ph.UserId = u.Id AND b."Date">=CAST('2010-07-20 10:34:10' AS TIMESTAMP) AND ph.PostHistoryTypeId=5
