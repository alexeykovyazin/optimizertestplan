SELECT COUNT(*) FROM postHistory as ph, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = ph.UserId AND ph.PostHistoryTypeId=2 AND p.AnswerCount>=0 AND p.FavoriteCount>=0
