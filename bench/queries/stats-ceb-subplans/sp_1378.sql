SELECT COUNT(*) FROM users as u, posts as p, postHistory as ph WHERE u.Id = p.OwnerUserId AND p.Id = ph.PostId AND u.Reputation<=240 AND p.Score<=21 AND p.AnswerCount<=3 AND p.FavoriteCount>=0
