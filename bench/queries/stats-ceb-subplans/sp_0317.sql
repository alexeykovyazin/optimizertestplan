SELECT COUNT(*) FROM users as u, posts as p WHERE p.OwnerUserId = u.Id AND u.DownVotes>=0 AND p.Score<=13 AND p.AnswerCount>=0 AND p.AnswerCount<=4 AND p.CommentCount>=0 AND p.FavoriteCount<=2
