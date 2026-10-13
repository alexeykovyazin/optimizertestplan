SELECT COUNT(*) FROM postHistory as ph, comments as c, users as u WHERE c.UserId = u.Id AND ph.UserId = u.Id AND ph.PostHistoryTypeId=1 AND ph.CreationDate>=CAST('2010-09-14 11:59:07' AS TIMESTAMP)
