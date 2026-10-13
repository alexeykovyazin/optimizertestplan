SELECT COUNT(*) FROM users as u, posts as p WHERE p.OwnerUserId = u.Id AND u.DownVotes=0 AND u.UpVotes>=0 AND u.UpVotes<=244 AND p.Score>=-1 AND p.CommentCount>=0 AND p.CommentCount<=23
