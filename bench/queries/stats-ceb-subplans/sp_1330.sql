SELECT COUNT(*) FROM votes as v, posts as p WHERE p.Id = v.PostId AND v.BountyAmount<=50 AND p.PostTypeId=1 AND p.CommentCount>=0 AND p.CommentCount<=12 AND p.FavoriteCount>=0
