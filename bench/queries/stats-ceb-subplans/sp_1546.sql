SELECT COUNT(*) FROM badges as b, votes as v, posts as p, users as u WHERE u.Id = p.OwnerUserId AND u.Id = b.UserId AND u.Id = v.UserId AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=15
