SELECT COUNT(*) FROM users as u, posts as p WHERE u.Id = p.OwnerUserId AND u.Reputation<=240 AND p.Score<=21 AND p.AnswerCount<=3 AND p.FavoriteCount>=0
