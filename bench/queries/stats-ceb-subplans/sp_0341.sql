SELECT COUNT(*) FROM badges as b, postHistory as ph, users as u WHERE b.UserId = u.Id AND ph.UserId = u.Id AND ph.PostHistoryTypeId=12
