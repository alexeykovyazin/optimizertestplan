SELECT COUNT(*) FROM postLinks as pl, posts as p WHERE p.Id = pl.PostId AND p.PostTypeId=1 AND p.FavoriteCount>=0 AND p.FavoriteCount<=2
