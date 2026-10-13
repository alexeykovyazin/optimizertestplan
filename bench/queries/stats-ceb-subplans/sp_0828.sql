SELECT COUNT(*) FROM postHistory as ph, posts as p WHERE p.Id = ph.PostId AND ph.PostHistoryTypeId=5 AND p.PostTypeId=1 AND p.FavoriteCount>=0 AND p.FavoriteCount<=2
