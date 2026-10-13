SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE u.Id = b.UserId AND u.Id = ph.UserId AND ph.PostHistoryTypeId=5 AND ph.CreationDate>=CAST('2011-01-31 15:35:37' AS TIMESTAMP)
